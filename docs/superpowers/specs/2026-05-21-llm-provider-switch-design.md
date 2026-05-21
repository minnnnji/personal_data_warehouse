# LLM Provider 전환 설계

**날짜:** 2026-05-21  
**대상 파일:** `backend/llm_service.py`, `.env`

---

## 목표

현재 Anthropic Claude API에 의존하는 `llm_service.py`를 사내 폐쇄망 LLM(ADXP agent_gateway)으로 전환한다. 개발 중엔 Anthropic, 사내 배포 시엔 내부 LLM을 `.env` 한 줄 수정으로 전환할 수 있도록 한다.

---

## 환경변수 구성

`.env` 파일에 두 provider의 키를 모두 보유하고, `LLM_PROVIDER`로 전환한다.

```
# Anthropic (개발용)
ANTHROPIC_API_KEY=sk-ant-...

# 사내 LLM (배포용)
LLM_PROVIDER=internal          # "internal" | "anthropic" (기본값: anthropic)
INTERNAL_LLM_AGENT_ID=your-agent-id
INTERNAL_LLM_API_KEY=your-api-key
```

- `LLM_PROVIDER`가 없거나 `"anthropic"`이면 기존 Anthropic SDK 경로로 동작
- `LLM_PROVIDER=internal`이면 사내 API 경로로 동작

---

## 사내 LLM API 스펙

| 항목 | 값 |
|---|---|
| URL | `https://adxp.adotbiz.ai/api/v1/agent_gateway/{agent_id}/invoke` |
| Method | POST |
| Headers | `Authorization: Bearer <api-key>`, `Content-Type: application/json` |

**Request Body:**
```json
{
  "config": {},
  "input": {
    "messages": [{"content": "<prompt>", "type": "human"}],
    "additional_kwargs": {}
  },
  "kwargs": {}
}
```

**Response:** `response["output"]["content"]`에 최종 텍스트 답변이 담긴다.  
> ⚠️ API 문서 기준 `output.content` 타입이 Object로 명시되어 있어, 실제 텍스트 추출 경로(`["content"]` 직접 접근인지, 내부 하위 키가 있는지)는 구현 시 실제 응답을 확인해 결정한다.

---

## 구조 변경

변경 범위는 `backend/llm_service.py` 단일 파일이다.

### 기존 구조
```
각 함수 → get_client().messages.create() → response.content[0].text
```

### 변경 후 구조
```
각 함수 → _call_llm(prompt: str) → str
               ↓
   LLM_PROVIDER == "internal"?
   ├── Yes: httpx.post(agent_gateway URL) → response["output"]["content"]
   └── No:  anthropic SDK → response.content[0].text
```

- `generate_metadata`, `search_files`, `generate_combine_code` 3개 함수의 프롬프트 구성 로직은 변경하지 않는다
- API 호출 코드만 `_call_llm(prompt)` 단일 호출로 교체한다
- `get_client()`는 Anthropic 경로에서만 사용하도록 유지한다

---

## 에러 처리

| 상황 | 처리 방식 |
|---|---|
| `INTERNAL_LLM_AGENT_ID` 또는 `INTERNAL_LLM_API_KEY` 미설정 | `RuntimeError` — 앱 기동 시점에 즉시 감지 |
| `LLM_PROVIDER`가 `"internal"`도 `"anthropic"`도 아닌 값 | `ValueError` |
| 사내 API HTTP 4xx/5xx 응답 | `httpx.HTTPStatusError` raise |
| `output.content`가 예상 구조가 아닌 경우 | `ValueError` raise |
| JSON 파싱 실패 (기존 로직) | 기존 `_extract_json()` 3회 retry 유지 |

---

## LLM으로 전송되는 데이터 범위

폐쇄망 내 사내 LLM이라도 어떤 데이터가 전송되는지 명확히 기록한다.

| 호출 함수 | 전송 데이터 | 실제 데이터 포함 여부 |
|---|---|---|
| `generate_metadata` | 컬럼명, dtype, **샘플 데이터 최대 5행**, 원본 파일명 | ✅ 실제 셀 값 포함 |
| `search_files` | 파일 메타데이터 전체 (표준화명, 설명, 태그, 프로젝트명, 컬럼명, 행수), 사용자 검색어 | ❌ 실제 데이터 미포함 (메타데이터만) |
| `generate_combine_code` | 컬럼명, dtype, 행수, 사용자 명령어 | ❌ 실제 데이터 미포함 (스키마만) |

**핵심 정리:**
- `generate_metadata`만 실제 데이터(샘플 5행)를 전송한다. 나머지 두 함수는 스키마·메타데이터만 전송.
- 사내 LLM 서버가 사내망 내에 있는 경우, 위 데이터는 망 외부로 나가지 않는다.
- 개발 중 `LLM_PROVIDER=anthropic` 사용 시엔 샘플 데이터 5행이 Anthropic 외부 서버로 전송됨에 주의.

---

## 의존성 변경

- `httpx` 패키지를 `requirements.txt`에 추가 (사내 API HTTP 호출용)
- `anthropic` 패키지는 제거하지 않고 유지 (Anthropic 경로 공존)

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|---|---|
| `backend/llm_service.py` | `_call_llm()` 헬퍼 추가, 3개 함수의 API 호출 교체 |
| `.env` | `LLM_PROVIDER`, `INTERNAL_LLM_AGENT_ID`, `INTERNAL_LLM_API_KEY` 추가 |
| `requirements.txt` | `httpx` 추가 |
