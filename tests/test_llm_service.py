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
