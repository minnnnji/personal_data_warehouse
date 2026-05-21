import json
import os
from typing import Any, Dict, List, Optional

import anthropic
import httpx

_INTERNAL_LLM_BASE_URL = "https://adxp.adotbiz.ai/api/v1/agent_gateway"

_client: Optional[anthropic.Anthropic] = None
MODEL = "claude-sonnet-4-6"


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일 또는 환경변수를 확인하세요."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _extract_json(text: str) -> dict:
    """LLM 응답에서 JSON 블록을 추출하여 파싱."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        import ast
        result = ast.literal_eval(text)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {text[:200]}")


def _call_internal_llm(prompt: str) -> str:
    """사내 ADXP agent_gateway LLM API 호출."""
    agent_id = os.environ.get("INTERNAL_LLM_AGENT_ID")
    api_key = os.environ.get("INTERNAL_LLM_API_KEY")
    if not agent_id or not api_key:
        raise RuntimeError(
            "INTERNAL_LLM_AGENT_ID 또는 INTERNAL_LLM_API_KEY 환경변수가 설정되지 않았습니다."
        )

    url = f"{_INTERNAL_LLM_BASE_URL}/{agent_id}/invoke"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {
        "config": {},
        "input": {
            "messages": [{"content": prompt, "type": "human"}],
            "additional_kwargs": {},
        },
        "kwargs": {},
    }

    response = httpx.post(url, headers=headers, json=body, timeout=60.0)
    response.raise_for_status()
    data = response.json()

    output = data.get("output", {})
    content = output.get("content")
    if content is None:
        raise ValueError(f"사내 LLM 응답에서 output.content를 찾을 수 없습니다: {data}")
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return content.get("content") or content.get("text") or str(content)
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def _call_llm(prompt: str, max_tokens: int = 2048) -> str:
    """LLM_PROVIDER 환경변수에 따라 Anthropic 또는 사내 LLM 호출."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic")
    if provider == "internal":
        return _call_internal_llm(prompt)
    elif provider == "anthropic":
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    else:
        raise ValueError(
            f"알 수 없는 LLM_PROVIDER 값: '{provider}'. 'internal' 또는 'anthropic'만 허용됩니다."
        )


def generate_metadata(
    columns_info: List[Dict[str, Any]],
    sample_rows: List[Dict[str, Any]],
    filename: str,
    conventions: Optional[Dict[str, List[Dict]]] = None,
    existing_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """파일 샘플을 분석해 메타데이터 JSON을 자동 생성."""

    # 네이밍 컨벤션 컨텍스트 구성
    convention_section = ""
    if conventions:
        lines = []
        for field, items in conventions.items():
            if items:
                values = ", ".join(f"{i['value']}({i.get('description', '')})" for i in items)
                lines.append(f"- {field}: {values}")
        if lines:
            convention_section = "\n네이밍 컨벤션:\n" + "\n".join(lines)

    existing_section = ""
    if existing_names:
        existing_section = f"\n기존 파일 표준화 이름 목록 (패턴 참고):\n" + "\n".join(f"- {n}" for n in existing_names[:20])

    prompt = f"""당신은 데이터 분석 전문가입니다. 업로드된 데이터 파일의 메타데이터를 자동으로 생성해주세요.

파일명: {filename}
{convention_section}
{existing_section}

컬럼 정보:
{json.dumps(columns_info, ensure_ascii=False, indent=2)}

샘플 데이터 (최대 5행):
{json.dumps(sample_rows, ensure_ascii=False, indent=2)}

위 정보를 분석하여 반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 절대 포함하지 마세요.

{{
  "standardized_name": "컨벤션 규칙에 따른 표준화 이름 (예: PR_A제품_raw_iqc_v1). 형식: {{domain}}_{{product_name}}_{{data_type}}_{{stage}}_v1",
  "product_name": "파일에서 추정되는 제품명 또는 빈 문자열",
  "description": "이 데이터가 무엇인지 한국어로 2~3문장 설명",
  "category": "데이터 카테고리 단어 하나 (생산, 품질, 영업, 물류, 인사, 재무, 설비, 기타 중 선택)",
  "tags": ["관련 키워드", "태그", "최대 5개"],
  "project_guess": "추정되는 프로젝트명 또는 빈 문자열",
  "uncertain": false,
  "question_for_user": null
}}

standardized_name 생성 규칙:
- domain: 네이밍 컨벤션의 domain 값 중 가장 적합한 것 선택 (없으면 카테고리 기반 추정)
- product_name: 파일 내용에서 추정 (불명확하면 빈 문자열)
- data_type: 네이밍 컨벤션의 data_type 값 중 적합한 것 선택 (없으면 raw/model/report 중 추정)
- stage: 네이밍 컨벤션의 stage 값 중 적합한 것 선택 (없으면 raw/cleaned/report 중 추정)

데이터의 맥락이 불분명하여 추가 정보가 꼭 필요한 경우에만:
- uncertain을 true로 설정
- question_for_user에 사용자에게 물어볼 구체적인 한국어 질문 작성"""

    return _extract_json(_call_llm(prompt, max_tokens=1024))


def search_files(query: str, all_metadata: List[Dict[str, Any]]) -> str:
    """자연어 질의에 맞는 파일을 메타데이터 기반으로 검색·설명."""
    summaries = [
        {
            "id": m["id"],
            "standardized_name": m.get("standardized_name") or m["original_filename"],
            "original_filename": m["original_filename"],
            "category": m["category"],
            "description": m["description"],
            "tags": m["tags"],
            "project_name": m["project_name"],
            "product_name": m.get("product_name", ""),
            "columns": [c["name"] for c in m["columns_info"]],
            "row_count": m["row_count"],
        }
        for m in all_metadata
    ]

    prompt = f"""당신은 데이터 창고 검색 도우미입니다. 사용자의 질의에 맞는 데이터 파일을 찾아 설명해주세요.

저장된 데이터 파일 목록:
{json.dumps(summaries, ensure_ascii=False, indent=2)}

사용자 질의: {query}

관련 있는 파일들을 찾아 한국어로 답변하세요. 각 파일이 왜 관련 있는지 구체적으로 설명하고, 파일 ID (id 필드)도 함께 명시해주세요.
관련 파일이 없다면 그렇게 알려주세요. 답변은 마크다운 형식으로 작성하세요."""

    return _call_llm(prompt, max_tokens=2048)


def generate_combine_code(
    files_info: List[Dict[str, Any]], command: str
) -> str:
    """자연어 결합 명령을 pandas 코드로 변환."""
    files_desc = [
        {
            "variable": f"df_{i}",
            "filename": f.get("standardized_name") or f["original_filename"],
            "columns": [c["name"] for c in f["columns_info"]],
            "dtypes": {c["name"]: c["dtype"] for c in f["columns_info"]},
            "row_count": f["row_count"],
        }
        for i, f in enumerate(files_info)
    ]

    prompt = f"""당신은 pandas 전문가입니다. 사용자의 명령을 실행하는 pandas 코드를 생성해주세요.

사용 가능한 데이터프레임 (이미 로드되어 있음):
{json.dumps(files_desc, ensure_ascii=False, indent=2)}

사용자 명령: {command}

반드시 아래 규칙을 따르세요:
1. 입력 데이터프레임 변수명은 df_0, df_1, ... 으로 이미 정의되어 있습니다
2. 최종 결과는 반드시 result_df 변수에 저장하세요
3. pandas(pd)와 numpy(np)만 사용 가능합니다
4. import 문을 절대 포함하지 마세요
5. 실행 가능한 순수 Python/pandas 코드만 반환하세요
6. 코드 블록 마크다운(```) 없이 코드만 반환하세요
7. 주석은 한국어로 작성하세요

코드:"""

    code = _call_llm(prompt, max_tokens=2048).strip()
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    return code
