# Personal Data Warehouse — CLAUDE.md

## 프로젝트 개요

데이터 분석가가 여러 프로젝트에 걸쳐 흩어진 데이터 파일들을 하나의 저장소에서 관리하는 개인용 데이터 창고 웹앱.
LLM이 파일 내용을 인식해 표준화된 이름으로 저장하고, 날짜/키 범위 기반 스마트 병합, 데이터 계보(Lineage) 추적, 자연어 기반 탐색·조작 기능을 제공한다.

---

## 기술 스택

| 역할 | 기술 |
|---|---|
| 백엔드 API | FastAPI |
| 프론트엔드 | Streamlit |
| 메타데이터 DB | SQLite (sqlite3, ORM 사용 금지) |
| 파일 저장소 | 로컬 디렉토리 (`./storage/`) |
| LLM | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| 그래프 시각화 | pyvis |
| 데이터 처리 | pandas, numpy |
| 기타 | python-multipart, aiofiles |

---

## 코딩 규칙 (반드시 준수)

- 모든 주석은 한국어로 작성
- DB 연결은 반드시 `contextmanager` 패턴 사용, 커넥션 직접 노출 금지
- ORM 사용 금지 — 모든 쿼리는 파라미터화된 raw SQL (`?` 플레이스홀더)
- LLM 응답은 항상 JSON 파싱 실패에 대한 fallback 처리 포함
- `/combine` 실행 코드 샌드박스: `{"pd": pandas, "np": numpy}` 만 허용, `import`, `os`, `sys`, `open`, `eval`, `exec`, `__` 포함 시 실행 거부
- 환경변수: `ANTHROPIC_API_KEY` (`.env` 파일, python-dotenv로 로드)
- 모든 파일 I/O는 `pathlib.Path` 사용

---

## 파일 구조

```
data_warehouse/
├── CLAUDE.md
├── .env                     # ANTHROPIC_API_KEY
├── requirements.txt
├── backend/
│   ├── main.py              # FastAPI 앱, 라우터 등록
│   ├── db.py                # SQLite 연결 contextmanager, 초기화
│   ├── schemas.py           # Pydantic 모델
│   ├── file_handler.py      # 파일 읽기/저장/변환 유틸
│   ├── llm_service.py       # Anthropic API 호출 전담
│   ├── routers/
│   │   ├── upload.py        # POST /upload
│   │   ├── files.py         # GET /files, /files/{id}/preview, /files/{id}/download
│   │   ├── query.py         # POST /query (자연어 검색)
│   │   ├── combine.py       # POST /combine (자연어 병합)
│   │   ├── lineage.py       # GET /lineage (그래프 데이터)
│   │   └── convention.py    # GET/POST /convention (네이밍 컨벤션 관리)
│   └── utils/
│       └── range_detector.py # 날짜/키 범위 감지 로직
├── frontend/
│   └── app.py               # Streamlit 멀티탭 UI
├── storage/                 # 실제 파일 저장 디렉토리 (자동 생성)
├── warehouse.db             # SQLite DB (자동 생성)
└── temp/                    # 병합 결과 임시 파일 (자동 생성)
```

---

## DB 스키마

### files 테이블

```sql
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,                  -- UUID4 앞 8자리
    original_filename TEXT NOT NULL,      -- 업로드 원본 파일명
    standardized_name TEXT NOT NULL,      -- LLM이 생성한 표준화 이름 (확장자 제외)
    storage_path TEXT NOT NULL,           -- 실제 저장 경로
    category TEXT,                        -- 도메인 카테고리 (예: PR, WFR, IQC)
    project TEXT,                         -- 프로젝트명
    description TEXT,                     -- LLM이 생성한 한국어 설명
    tags TEXT,                            -- JSON 배열 문자열 (예: '["lot_id","cd","thickness"]')
    columns_info TEXT,                    -- JSON 객체 {컬럼명: 타입} 문자열
    row_count INTEGER,                    -- 행 수
    range_column TEXT,                    -- 범위 기준 컬럼명 (예: reg_date, lot_id)
    range_min TEXT,                       -- 범위 최솟값 (문자열로 통일)
    range_max TEXT,                       -- 범위 최댓값
    range_type TEXT,                      -- 'date' | 'string' | 'numeric' | null
    version INTEGER DEFAULT 1,            -- 같은 계열 내 버전
    file_format TEXT,                     -- 'pkl' | 'csv' | 'parquet' | 'xlsx'
    uploaded_at TEXT NOT NULL             -- ISO8601 문자열
);
```

### lineage 테이블

```sql
CREATE TABLE IF NOT EXISTS lineage (
    id TEXT PRIMARY KEY,
    source_ids TEXT NOT NULL,             -- JSON 배열: 입력 파일 ID들
    output_id TEXT NOT NULL,             -- 결과 파일 ID (files 테이블 참조)
    operation TEXT NOT NULL,             -- 'concat' | 'merge' | 'smart_merge' | 'filter'
    operation_detail TEXT,               -- JSON: 사용된 pandas 코드, merge 키, 병합 정책 등
    created_at TEXT NOT NULL
);
```

### naming_convention 테이블

```sql
CREATE TABLE IF NOT EXISTS naming_convention (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field TEXT NOT NULL,                  -- 'domain' | 'data_type' | 'stage'
    value TEXT NOT NULL,                  -- 예: 'PR', 'raw', 'cleaned'
    description TEXT,                     -- 한국어 설명
    created_at TEXT NOT NULL
);
```

---

## 기능 명세

### 1. 파일 업로드 + 메타데이터 자동인식 (`POST /upload`)

**처리 흐름:**
1. 파일 수신 → UUID 생성 → 임시 저장
2. `file_handler.py`에서 포맷별 읽기: pkl/csv/parquet/xlsx 모두 지원
3. 상위 5행 + 컬럼명 + dtype 정보 추출
4. `llm_service.py`의 `analyze_file()` 호출 → 아래 JSON 반환 요청

```json
{
  "standardized_name": "PR_raw_iqc_coa_v1",
  "category": "PR",
  "project": "Smart DoE",
  "description": "포토레지스트 원료 IQC-COA 비교 데이터. lot_id 기준으로 입고 기준값과 실측값 포함.",
  "tags": ["lot_id", "iqc", "coa", "원료"],
  "range_column": "reg_date",
  "range_type": "date",
  "uncertain": false,
  "question_for_user": null
}
```

5. `uncertain: true`이면 질문과 함께 미확정 상태로 응답
6. 사용자 확정 요청(`POST /upload/confirm`) 시 DB 저장 + 파일 영구 저장

**네이밍 컨벤션 활용:**
- LLM 프롬프트에 현재 저장된 `naming_convention` 테이블 전체 + 기존 파일명 목록 포함
- "기존 파일들의 네이밍 패턴을 참고해 일관된 이름을 생성하라"는 지시 포함

---

### 2. 범위 감지 스마트 병합 (업로드 시 자동 트리거)

**`range_detector.py` 역할:**
- 신규 파일과 동일 `category` + `project` 파일들의 범위 비교
- 겹침 구간 계산 후 사용자에게 선택지 제시

**겹침 감지 응답 예시:**
```json
{
  "overlap_detected": true,
  "existing_file": {"id": "abc12345", "name": "PR_raw_iqc_coa_v1", "range": ["2025-03-13", "2025-06-18"]},
  "new_file_range": ["2025-05-13", "2025-09-19"],
  "overlap_range": ["2025-05-13", "2025-06-18"],
  "overlap_row_estimate": 347,
  "merge_options": [
    {"key": "new_priority", "label": "신규 데이터 우선 (겹치는 구간은 새 파일 기준)"},
    {"key": "old_priority", "label": "기존 데이터 유지"},
    {"key": "manual", "label": "겹치는 행 확인 후 수동 결정"},
    {"key": "separate", "label": "별도 파일로 저장 (병합 안 함)"}
  ]
}
```

**병합 정책 선택 후 (`POST /upload/merge`):**
- 선택한 정책으로 pandas 병합 실행
- 결과를 새 버전으로 저장 (예: `PR_raw_iqc_coa_v3`)
- lineage 테이블에 기록: `source_ids: [v1_id, v2_id]`, `operation: "smart_merge"`, `operation_detail: {policy, overlap_range, excluded_rows}`

---

### 3. 네이밍 표준화 관리 (`GET/POST /convention`)

- 사용자가 도메인·데이터종류·처리단계 목록을 직접 정의
- 새 값 추가 시 DB에 저장
- LLM이 파일 분석할 때마다 이 목록을 컨텍스트로 전달
- **소급 정리 제안**: `POST /convention/suggest-rename` → 기존 파일 전체를 보고 컨벤션과 불일치하는 파일명 목록 + 제안 이름 반환. 사용자 일괄 승인 가능.

---

### 4. 파일 미리보기 (`GET /files/{id}/preview`)

- 포맷별 읽기: `pd.read_pickle`, `pd.read_csv`, `pd.read_parquet`, `pd.read_excel`
- 최대 100행, JSON 직렬화 (`orient="records"`)
- `range_column`이 있으면 해당 컬럼 기준 정렬 후 반환
- null/NaN은 `null`로 직렬화

---

### 5. 자연어 검색 (`POST /query`)

**LLM 프롬프트 구성:**
- 컨텍스트: 전체 파일의 `standardized_name`, `description`, `tags`, `range_min/max`, `project` 목록
- 사용자 질의 포함
- 응답 형식: 관련 파일 ID 목록 + 각 파일에 대한 한국어 설명 + 추천 이유

---

### 6. 자연어 Concat/Join (`POST /combine`)

**처리 흐름:**
1. 파일 ID 목록 + 자연어 명령 수신
2. 각 파일의 `columns_info` + `range_column` + 명령을 LLM에 전달
3. LLM이 pandas 코드 생성 (변수명 규칙: 입력은 `df_0`, `df_1`, ... / 결과는 반드시 `result_df`)
4. 코드 보안 검사 후 샌드박스 실행
5. 결과를 `temp/` 에 저장, 다운로드 URL 반환
6. 사용자가 결과 저장 확정 시 → `POST /combine/save` → files + lineage 테이블에 정식 저장

**응답에 반드시 포함:**
- 생성된 pandas 코드 (사용자 검토용)
- 결과 미리보기 (상위 20행)
- 결과 행/열 수

---

### 7. Lineage Graph (`GET /lineage`)

- `lineage` 테이블 전체 조회
- pyvis `Network` 객체로 그래프 생성
- 노드: 각 파일 (`standardized_name`, `range_min~range_max`, `row_count` 표시)
- 엣지: lineage 관계 (`operation` 타입을 엣지 레이블로)
- HTML 파일로 렌더링 후 Streamlit `components.html()`로 임베드
- 노드 색상: raw=파란색, merged=초록색, modeled=주황색

---

## API 엔드포인트 요약

| Method | Path | 설명 |
|---|---|---|
| POST | `/upload` | 파일 업로드 + LLM 분석 |
| POST | `/upload/confirm` | 메타데이터 확정 + 저장 |
| POST | `/upload/merge` | 겹침 감지 후 병합 정책 실행 |
| GET | `/files` | 파일 목록 (category/project/tag 필터) |
| GET | `/files/{id}/preview` | 파일 미리보기 (최대 100행) |
| GET | `/files/{id}/download` | 파일 다운로드 (format 쿼리파라미터: csv/pkl/xlsx) |
| PATCH | `/files/{id}` | 메타데이터 수정 |
| POST | `/query` | 자연어 검색 |
| POST | `/combine` | 자연어 병합 (코드 생성 + 실행) |
| POST | `/combine/save` | 병합 결과 정식 저장 |
| GET | `/lineage` | lineage 그래프 HTML |
| GET | `/convention` | 네이밍 컨벤션 목록 |
| POST | `/convention` | 컨벤션 항목 추가 |
| POST | `/convention/suggest-rename` | 기존 파일 소급 정리 제안 |

---

## Streamlit UI 구조 (`frontend/app.py`)

### 탭 구성

```
[📁 파일 창고]  [⬆️ 업로드]  [🔍 검색]  [🔗 결합]  [🕸️ Lineage]  [⚙️ 컨벤션 설정]
```

### 📁 파일 창고
- 사이드바: category / project / tag 멀티셀렉트 필터
- 파일 카드: `standardized_name`, `description`, `tags`, `range_min~max`, `row_count x col_count`
- 카드 내 버튼: [미리보기 ▼] [CSV 다운로드] [PKL 다운로드] [XLSX 다운로드]
- 미리보기 클릭 시 카드 아래에 `st.dataframe()` 인라인 펼침

### ⬆️ 업로드
- `st.file_uploader` (다중 업로드 지원)
- 업로드 후 LLM 분석 결과를 편집 가능한 폼으로 표시
- `uncertain: true` 시 LLM 질문 표시 + 답변 입력란
- 겹침 감지 시 범위 비교 시각화 + 병합 정책 선택 라디오버튼
- [저장 확정] 버튼

### 🔍 검색
- 자연어 입력창 + [검색] 버튼
- LLM 답변 텍스트 표시
- 관련 파일 카드 목록 표시 (📁 탭과 동일한 카드 컴포넌트 재사용)

### 🔗 결합
- 파일 목록에서 체크박스로 2개 이상 선택
- 선택된 파일들의 컬럼 정보 나란히 표시
- 자연어 명령 입력 (예: "lot_id 기준으로 left join해줘")
- [코드 생성] → `st.code()`로 pandas 코드 표시
- [실행] 버튼 (사용자가 코드 확인 후 실행)
- 결과 미리보기 + [이 결과 창고에 저장] + [다운로드]

### 🕸️ Lineage
- pyvis 그래프 `st.components.v1.html()`로 임베드
- 노드 클릭 시 우측 패널에 파일 메타데이터 표시

### ⚙️ 컨벤션 설정
- 현재 컨벤션 테이블 표시 (domain / data_type / stage 분류)
- 새 항목 추가 폼
- [소급 정리 제안 받기] 버튼 → LLM 제안 목록 표시 + 체크박스로 선택 적용

---

## LLM 프롬프트 설계 원칙

### 공통
- 모든 LLM 응답은 JSON only 강제: `"반드시 JSON만 반환하고 마크다운 코드블록이나 다른 텍스트는 포함하지 마라"`
- 응답 파싱 실패 시 3회 retry 후 에러 반환

### 파일 분석 프롬프트 (`analyze_file`)
```
컨텍스트:
- 현재 네이밍 컨벤션: {naming_convention 테이블 전체}
- 기존 파일 목록: {standardized_name 리스트}
- 신규 파일 샘플: 컬럼명={columns}, 상위5행={sample_rows}

지시:
위 컨벤션 규칙과 기존 파일명 패턴을 엄격히 따라 standardized_name을 생성하라.
uncertain이 true인 경우 question_for_user에 구체적인 한국어 질문을 작성하라.
```

### 병합 코드 생성 프롬프트 (`generate_combine_code`)
```
컨텍스트:
- df_0: {file_0의 columns_info, range_column, row_count}
- df_1: {file_1의 columns_info, range_column, row_count}
- 사용자 명령: {user_command}

지시:
실행 가능한 pandas 코드만 반환하라. import 금지.
입력 변수는 df_0, df_1이고 결과는 반드시 result_df에 저장하라.
```

---

## 구현 순서 (Phase)

### Phase 1 — 핵심 창고
- DB 초기화 (`db.py`)
- 파일 업로드 + LLM 분석 + 저장 (`/upload`, `/upload/confirm`)
- 파일 목록 + 미리보기 + 다운로드 (`/files`)
- Streamlit [📁 창고] + [⬆️ 업로드] 탭

### Phase 2 — 네이밍 표준화
- `naming_convention` 테이블 + `/convention` 엔드포인트
- LLM 분석 프롬프트에 컨벤션 컨텍스트 주입
- 소급 정리 제안 기능
- Streamlit [⚙️ 컨벤션 설정] 탭

### Phase 3 — 스마트 병합
- `range_detector.py` 범위 감지 로직
- `/upload/merge` 엔드포인트
- 업로드 탭에 겹침 감지 UI 추가

### Phase 4 — 자연어 기능
- `/query` 자연어 검색
- `/combine` 자연어 병합 + 샌드박스 실행
- Streamlit [🔍 검색] + [🔗 결합] 탭

### Phase 5 — Lineage Graph
- `lineage` 테이블 + `/lineage` 엔드포인트
- pyvis 그래프 생성
- Streamlit [🕸️ Lineage] 탭

---

## requirements.txt

```
fastapi
uvicorn[standard]
streamlit
anthropic
pandas
numpy
pyarrow
openpyxl
python-multipart
aiofiles
pyvis
python-dotenv
pydantic
requests
```