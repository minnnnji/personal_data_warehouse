# LLM Provider 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `LLM_PROVIDER` 환경변수 하나로 Anthropic ↔ 사내 ADXP agent_gateway LLM을 런타임 전환한다.

**Architecture:** `llm_service.py` 내부에 `_call_llm(prompt)` 단일 진입점을 추가하고, `LLM_PROVIDER=internal`이면 httpx로 사내 API를 호출하고 아니면 기존 Anthropic SDK 경로를 사용한다. 기존 3개 public 함수의 프롬프트 로직은 변경하지 않고 API 호출부만 `_call_llm()`으로 교체한다.

**Tech Stack:** Python 3.x, httpx, anthropic SDK, pytest, unittest.mock

---

## 변경 파일 목록

| 파일 | 역할 |
|---|---|
| `requirements.txt` | `httpx` 추가 |
| `backend/llm_service.py` | `_call_internal_llm()`, `_call_llm()` 추가 / 기존 3개 함수 교체 |
| `tests/test_llm_service.py` | 신규 — 디스패처·내부 LLM 클라이언트·public 함수 단위 테스트 |
| `.env` | `LLM_PROVIDER`, `INTERNAL_LLM_AGENT_ID`, `INTERNAL_LLM_API_KEY` 추가 (버전 관리 제외) |

---

## Task 1: httpx 의존성 추가

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: requirements.txt에 httpx 추가**

`# Utilities` 블록에 아래 줄 추가:
```
httpx==0.27.2
```

최종 Utilities 블록:
```
# Utilities
python-multipart==0.0.17
python-dotenv==1.0.1
requests==2.32.3
httpx==0.27.2
```

- [ ] **Step 2: 설치**

```bash
pip install httpx==0.27.2
```

Expected: `Successfully installed httpx-0.27.2` 또는 이미 설치된 경우 메시지 없음.

- [ ] **Step 3: 커밋**

```bash
git add requirements.txt
git commit -m "chore: httpx 의존성 추가 (사내 LLM API 호출용)"
```

---

## Task 2: 테스트 환경 세팅

**Files:**
- Create: `tests/test_llm_service.py`

- [ ] **Step 1: tests 디렉토리 생성 및 테스트 파일 생성**

`tests/test_llm_service.py`:
```python
import json
import os
import pytest
import httpx
from unittest.mock import patch, MagicMock

from backend.llm_service import (
    _call_llm,
    _call_internal_llm,
    generate_metadata,
    search_files,
    generate_combine_code,
)
```

- [ ] **Step 2: 임포트 동작 확인**

```bash
PYTHONPATH=. pytest tests/test_llm_service.py --collect-only
```

Expected:
```
collected 0 items
```
(테스트가 아직 없으므로 0개 — 임포트 에러가 없으면 정상)

---

## Task 3: `_call_llm` 디스패처 — 테스트 먼저

**Files:**
- Modify: `tests/test_llm_service.py`

- [ ] **Step 1: 디스패처 실패 테스트 작성**

`tests/test_llm_service.py`에 추가:
```python
# ── _call_llm 디스패처 테스트 ──────────────────────────────────────


def test_call_llm_defaults_to_anthropic_when_no_provider_set(monkeypatch):
    """LLM_PROVIDER 미설정 시 Anthropic 경로로 라우팅."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="anthropic result")]

    with patch("backend.llm_service._client", None), \
         patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_msg
        result = _call_llm("hello")

    assert result == "anthropic result"


def test_call_llm_routes_to_internal_when_provider_is_internal(monkeypatch):
    """LLM_PROVIDER=internal 시 _call_internal_llm 호출."""
    monkeypatch.setenv("LLM_PROVIDER", "internal")

    with patch("backend.llm_service._call_internal_llm", return_value="internal result") as mock:
        result = _call_llm("hello")

    assert result == "internal result"
    mock.assert_called_once_with("hello")


def test_call_llm_raises_for_unknown_provider(monkeypatch):
    """알 수 없는 LLM_PROVIDER 값이면 ValueError."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    with pytest.raises(ValueError, match="알 수 없는 LLM_PROVIDER"):
        _call_llm("hello")


def test_call_llm_passes_max_tokens_to_anthropic(monkeypatch):
    """max_tokens 인자가 Anthropic messages.create에 전달된다."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="ok")]

    with patch("backend.llm_service._client", None), \
         patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_msg
        _call_llm("hello", max_tokens=1024)
        call_kwargs = MockAnthropic.return_value.messages.create.call_args[1]

    assert call_kwargs["max_tokens"] == 1024
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```bash
PYTHONPATH=. pytest tests/test_llm_service.py -v
```

Expected: 4개 FAILED (`_call_llm` 미구현)

---

## Task 4: `_call_llm` 디스패처 구현

**Files:**
- Modify: `backend/llm_service.py`

- [ ] **Step 1: import에 httpx 추가 및 상수 선언**

`backend/llm_service.py` 상단을 아래로 교체:
```python
import json
import os
from typing import List, Dict, Any, Optional

import anthropic
import httpx

_client: Optional[anthropic.Anthropic] = None
MODEL = "claude-sonnet-4-6"
_INTERNAL_LLM_BASE_URL = "https://adxp.adotbiz.ai/api/v1/agent_gateway"
```

- [ ] **Step 2: `_call_llm` 함수 추가**

`_extract_json` 함수 바로 아래에 삽입:
```python
def _call_llm(prompt: str, max_tokens: int = 2048) -> str:
    """LLM_PROVIDER 환경변수에 따라 Anthropic 또는 사내 LLM을 호출한다."""
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
```

> `_call_internal_llm`은 Task 5에서 구현. 지금은 이름만 참조하므로 테스트 통과 가능.

- [ ] **Step 3: 테스트 실행 — PASS 확인**

```bash
PYTHONPATH=. pytest tests/test_llm_service.py::test_call_llm_defaults_to_anthropic_when_no_provider_set tests/test_llm_service.py::test_call_llm_routes_to_internal_when_provider_is_internal tests/test_llm_service.py::test_call_llm_raises_for_unknown_provider tests/test_llm_service.py::test_call_llm_passes_max_tokens_to_anthropic -v
```

Expected: 4개 PASSED

- [ ] **Step 4: 커밋**

```bash
git add backend/llm_service.py
git commit -m "feat: _call_llm 디스패처 추가 (LLM_PROVIDER 기반 라우팅)"
```

---

## Task 5: `_call_internal_llm` — 테스트 먼저

**Files:**
- Modify: `tests/test_llm_service.py`

- [ ] **Step 1: 내부 LLM 클라이언트 테스트 작성**

`tests/test_llm_service.py`에 추가:
```python
# ── _call_internal_llm 테스트 ──────────────────────────────────────


def test_call_internal_llm_raises_when_env_missing(monkeypatch):
    """INTERNAL_LLM_AGENT_ID 또는 API_KEY 미설정 시 RuntimeError."""
    monkeypatch.delenv("INTERNAL_LLM_AGENT_ID", raising=False)
    monkeypatch.delenv("INTERNAL_LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="INTERNAL_LLM_AGENT_ID"):
        _call_internal_llm("hello")


def test_call_internal_llm_correct_url_and_body(monkeypatch):
    """올바른 URL, 헤더, body 구조로 httpx.post를 호출한다."""
    monkeypatch.setenv("INTERNAL_LLM_AGENT_ID", "agent-123")
    monkeypatch.setenv("INTERNAL_LLM_API_KEY", "key-abc")

    mock_response = MagicMock()
    mock_response.json.return_value = {"output": {"content": "response text"}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response) as mock_post:
        result = _call_internal_llm("test prompt")

    assert result == "response text"
    args, kwargs = mock_post.call_args
    assert args[0] == "https://adxp.adotbiz.ai/api/v1/agent_gateway/agent-123/invoke"
    assert kwargs["headers"]["Authorization"] == "Bearer key-abc"
    assert kwargs["json"]["input"]["messages"][0]["content"] == "test prompt"
    assert kwargs["json"]["input"]["messages"][0]["type"] == "human"


def test_call_internal_llm_content_as_dict(monkeypatch):
    """output.content가 dict일 때 text 키에서 추출한다."""
    monkeypatch.setenv("INTERNAL_LLM_AGENT_ID", "agent-123")
    monkeypatch.setenv("INTERNAL_LLM_API_KEY", "key-abc")

    mock_response = MagicMock()
    mock_response.json.return_value = {"output": {"content": {"text": "dict result"}}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response):
        result = _call_internal_llm("hello")

    assert result == "dict result"


def test_call_internal_llm_content_as_list(monkeypatch):
    """output.content가 list일 때 text 블록을 이어 붙인다."""
    monkeypatch.setenv("INTERNAL_LLM_AGENT_ID", "agent-123")
    monkeypatch.setenv("INTERNAL_LLM_API_KEY", "key-abc")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "output": {"content": [{"type": "text", "text": "part1"}, {"type": "text", "text": "part2"}]}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response):
        result = _call_internal_llm("hello")

    assert result == "part1part2"


def test_call_internal_llm_missing_content_raises(monkeypatch):
    """output.content 키가 없으면 ValueError."""
    monkeypatch.setenv("INTERNAL_LLM_AGENT_ID", "agent-123")
    monkeypatch.setenv("INTERNAL_LLM_API_KEY", "key-abc")

    mock_response = MagicMock()
    mock_response.json.return_value = {"output": {}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response):
        with pytest.raises(ValueError, match="output.content"):
            _call_internal_llm("hello")


def test_call_internal_llm_http_error_propagates(monkeypatch):
    """사내 API가 4xx/5xx를 반환하면 HTTPStatusError가 전파된다."""
    monkeypatch.setenv("INTERNAL_LLM_AGENT_ID", "agent-123")
    monkeypatch.setenv("INTERNAL_LLM_API_KEY", "key-abc")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "403 Forbidden", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.post", return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            _call_internal_llm("hello")
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```bash
PYTHONPATH=. pytest tests/test_llm_service.py -k "internal" -v
```

Expected: 6개 FAILED (`_call_internal_llm` 미구현)

---

## Task 6: `_call_internal_llm` 구현

**Files:**
- Modify: `backend/llm_service.py`

- [ ] **Step 1: `_call_internal_llm` 함수 추가**

`_extract_json` 함수 바로 아래, `_call_llm` 위에 삽입:
```python
def _call_internal_llm(prompt: str) -> str:
    """사내 ADXP agent_gateway LLM API를 호출하고 텍스트 응답을 반환한다."""
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

    content = data.get("output", {}).get("content")
    if content is None:
        raise ValueError(f"사내 LLM 응답에서 output.content를 찾을 수 없습니다: {data}")
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return content.get("text", str(content))
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)
```

- [ ] **Step 2: 테스트 실행 — 전체 PASS 확인**

```bash
PYTHONPATH=. pytest tests/test_llm_service.py -v
```

Expected: 10개 PASSED

- [ ] **Step 3: 커밋**

```bash
git add backend/llm_service.py tests/test_llm_service.py
git commit -m "feat: _call_internal_llm 구현 및 테스트 추가"
```

---

## Task 7: public 함수 3개를 `_call_llm`으로 교체 — 테스트 먼저

**Files:**
- Modify: `tests/test_llm_service.py`

- [ ] **Step 1: public 함수 테스트 작성**

`tests/test_llm_service.py`에 추가:
```python
# ── public 함수 테스트 ─────────────────────────────────────────────

MOCK_METADATA_RESPONSE = json.dumps({
    "description": "테스트 데이터",
    "category": "품질",
    "tags": ["lot_id"],
    "project_guess": "",
    "uncertain": False,
    "question_for_user": "",
})


def test_generate_metadata_calls_call_llm_with_filename_and_columns():
    columns_info = [{"name": "lot_id", "dtype": "object"}, {"name": "cd", "dtype": "float64"}]
    sample_rows = [{"lot_id": "L001", "cd": 1.23}]

    with patch("backend.llm_service._call_llm", return_value=MOCK_METADATA_RESPONSE) as mock:
        result = generate_metadata(columns_info, sample_rows, "test_file.csv")

    assert mock.called
    prompt = mock.call_args[0][0]
    assert "test_file.csv" in prompt
    assert "lot_id" in prompt
    assert result["category"] == "품질"
    assert result["tags"] == ["lot_id"]


def test_generate_metadata_uses_max_tokens_1024():
    columns_info = [{"name": "col", "dtype": "int64"}]
    sample_rows = [{"col": 1}]

    with patch("backend.llm_service._call_llm", return_value=MOCK_METADATA_RESPONSE) as mock:
        generate_metadata(columns_info, sample_rows, "file.csv")

    _, kwargs = mock.call_args
    assert kwargs.get("max_tokens") == 1024


def test_search_files_calls_call_llm_with_query():
    all_metadata = [{
        "id": "abc123",
        "original_filename": "test.csv",
        "category": "품질",
        "description": "테스트",
        "tags": ["lot_id"],
        "project_name": "TestProject",
        "columns_info": [{"name": "lot_id"}],
        "row_count": 100,
    }]

    with patch("backend.llm_service._call_llm", return_value="관련 파일: test.csv") as mock:
        result = search_files("lot_id 관련 파일", all_metadata)

    assert mock.called
    prompt = mock.call_args[0][0]
    assert "lot_id 관련 파일" in prompt
    assert result == "관련 파일: test.csv"


def test_generate_combine_code_calls_call_llm_with_command():
    files_info = [
        {
            "original_filename": "a.csv",
            "columns_info": [{"name": "lot_id", "dtype": "object"}],
            "row_count": 50,
        },
        {
            "original_filename": "b.csv",
            "columns_info": [{"name": "lot_id", "dtype": "object"}, {"name": "cd", "dtype": "float64"}],
            "row_count": 80,
        },
    ]

    with patch("backend.llm_service._call_llm", return_value="result_df = pd.merge(df_0, df_1, on='lot_id')") as mock:
        result = generate_combine_code(files_info, "lot_id 기준으로 left join")

    assert mock.called
    prompt = mock.call_args[0][0]
    assert "lot_id 기준으로 left join" in prompt
    assert "df_0" in prompt
    assert "result_df" in result
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```bash
PYTHONPATH=. pytest tests/test_llm_service.py -k "generate or search" -v
```

Expected: 5개 FAILED (아직 기존 함수가 `_call_llm` 미사용)

---

## Task 8: public 함수 3개 교체 구현

**Files:**
- Modify: `backend/llm_service.py`

- [ ] **Step 1: `generate_metadata` 교체**

기존:
```python
    response = get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(response.content[0].text)
```

교체:
```python
    return _extract_json(_call_llm(prompt, max_tokens=1024))
```

- [ ] **Step 2: `search_files` 교체**

기존:
```python
    response = get_client().messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
```

교체:
```python
    return _call_llm(prompt, max_tokens=2048)
```

- [ ] **Step 3: `generate_combine_code` 교체**

기존:
```python
    response = get_client().messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    code = response.content[0].text.strip()
```

교체:
```python
    code = _call_llm(prompt, max_tokens=2048).strip()
```

- [ ] **Step 4: 전체 테스트 PASS 확인**

```bash
PYTHONPATH=. pytest tests/test_llm_service.py -v
```

Expected: 15개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add backend/llm_service.py tests/test_llm_service.py
git commit -m "feat: generate_metadata/search_files/generate_combine_code를 _call_llm으로 교체"
```

---

## Task 9: .env 환경변수 추가 및 실제 연결 검증

**Files:**
- Modify: `.env`

- [ ] **Step 1: .env에 사내 LLM 환경변수 추가**

`.env` 파일에 추가 (실제 값으로 교체):
```
# 사내 LLM (폐쇄망 배포용)
LLM_PROVIDER=anthropic
INTERNAL_LLM_AGENT_ID=실제-agent-id
INTERNAL_LLM_API_KEY=실제-api-key
```

> `LLM_PROVIDER=anthropic`으로 시작해 기존 기능이 정상인지 먼저 확인.

- [ ] **Step 2: 기존 Anthropic 경로 동작 확인**

백엔드 실행 후 파일 업로드 1건으로 `generate_metadata`가 정상 동작하는지 확인:
```bash
PYTHONPATH=. uvicorn backend.main:app --reload
```

- [ ] **Step 3: 사내 LLM으로 전환 후 연결 확인**

`.env`에서 `LLM_PROVIDER=internal`로 변경 후 서버 재시작, 파일 업로드 1건 테스트.

실제 응답을 보고 `output.content` 구조가 예상과 다르면 `_call_internal_llm` 내 추출 로직 수정:
- 문자열이면 → 현재 코드 그대로 정상
- `{"text": "..."}` 형태이면 → `isinstance(content, dict)` 분기가 처리
- 다른 구조이면 → 응답 전체를 출력해 확인 후 코드 수정

- [ ] **Step 4: 최종 커밋**

```bash
git add backend/llm_service.py
git commit -m "feat: LLM provider 전환 완성 — internal/anthropic env 기반 스위칭"
```
