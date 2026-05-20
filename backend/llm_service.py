import json
import os
from typing import List, Dict, Any, Optional

import anthropic

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
    return json.loads(text)


def generate_metadata(
    columns_info: List[Dict[str, Any]],
    sample_rows: List[Dict[str, Any]],
    filename: str,
) -> Dict[str, Any]:
    """파일 샘플을 분석해 메타데이터 JSON을 자동 생성."""
    prompt = f"""당신은 데이터 분석 전문가입니다. 업로드된 데이터 파일의 메타데이터를 자동으로 생성해주세요.

파일명: {filename}

컬럼 정보:
{json.dumps(columns_info, ensure_ascii=False, indent=2)}

샘플 데이터 (최대 5행):
{json.dumps(sample_rows, ensure_ascii=False, indent=2)}

위 정보를 분석하여 반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 절대 포함하지 마세요.

{{
  "description": "이 데이터가 무엇인지 한국어로 2~3문장 설명 (어떤 공정/업무/시스템 데이터인지, 주요 컬럼이 무엇인지 포함)",
  "category": "데이터 카테고리 단어 하나 (생산, 품질, 영업, 물류, 인사, 재무, 설비, 기타 중 선택)",
  "tags": ["관련 키워드", "태그", "최대 5개"],
  "project_guess": "추정되는 프로젝트명 또는 빈 문자열",
  "uncertain": false,
  "question_for_user": ""
}}

데이터의 맥락이 불분명하여 추가 정보가 꼭 필요한 경우에만:
- uncertain을 true로 설정
- question_for_user에 사용자에게 물어볼 구체적인 질문을 한국어로 작성"""

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(response.content[0].text)


def search_files(query: str, all_metadata: List[Dict[str, Any]]) -> str:
    """자연어 질의에 맞는 파일을 메타데이터 기반으로 검색·설명."""
    summaries = [
        {
            "id": m["id"],
            "filename": m["original_filename"],
            "category": m["category"],
            "description": m["description"],
            "tags": m["tags"],
            "project_name": m["project_name"],
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

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def generate_combine_code(
    files_info: List[Dict[str, Any]], command: str
) -> str:
    """자연어 결합 명령을 pandas 코드로 변환."""
    files_desc = [
        {
            "variable": f"df_{i}",
            "filename": f["original_filename"],
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

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    code = response.content[0].text.strip()
    # 코드 블록 마크다운 제거
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    return code
