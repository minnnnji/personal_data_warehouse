# Personal Data Warehouse — CLAUDE.md

## 실행 환경 제약

코드 작성만 수행하고 절대 직접 실행하지 말 것.
실행 환경이 분리되어 있음 (개발: 로컬 노트북 / 실행: 사내 VDI).
- `uvicorn`, `npm run`, `python` 등 실행 명령어 금지
- `pip install`, `npm install` 명령어 금지
- 터미널 명령 실행 금지
- 코드 작성 완료 후 "실행은 VDI에서 직접 해주세요" 로 마무리
## 프로젝트 개요

데이터 분석가가 여러 프로젝트에 걸쳐 흩어진 데이터 파일들을 하나의 저장소에서 관리하는 개인용 데이터 창고 웹앱.
LLM이 파일 내용을 인식해 표준화된 이름으로 저장하고, 날짜/키 범위 기반 스마트 병합, 데이터 계보(Lineage) 추적, 자연어 기반 탐색·조작 기능을 제공한다.

---

## 기술 스택

| 역할 | 기술 |
|---|---|
| 백엔드 API | FastAPI |
| 프론트엔드 | React 18 + Vite |
| UI 컴포넌트 | shadcn/ui |
| 스타일링 | Tailwind CSS v3 |
| 상태 관리 | TanStack Query v5 (서버 상태), Zustand (클라이언트 상태) |
| HTTP 클라이언트 | axios |
| 그래프 시각화 | React Flow (Lineage 그래프) |
| 테이블 | TanStack Table v8 |
| 메타데이터 DB | SQLite (sqlite3, ORM 사용 금지) |
| 파일 저장소 | 로컬 디렉토리 (`./storage/`) |
| LLM | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| 데이터 처리 | pandas, numpy |
| 기타 | python-multipart, aiofiles, python-dotenv |

---

## 코딩 규칙 (반드시 준수)

### 공통
- 모든 주석은 한국어로 작성

### 백엔드 (Python)
- DB 연결은 반드시 `contextmanager` 패턴 사용, 커넥션 직접 노출 금지
- ORM 사용 금지 — 모든 쿼리는 파라미터화된 raw SQL (`?` 플레이스홀더)
- LLM 응답은 항상 JSON 파싱 실패에 대한 fallback 처리 포함 (3회 retry)
- `/combine` 실행 코드 샌드박스: `{"pd": pandas, "np": numpy}` 만 허용
  - `import`, `os`, `sys`, `open`, `eval`, `exec`, `__` 문자열 포함 시 실행 즉시 거부
- 환경변수: `ANTHROPIC_API_KEY` (`.env` 파일, python-dotenv로 로드)
- 모든 파일 I/O는 `pathlib.Path` 사용
- FastAPI CORS 설정: `http://localhost:5173` 허용 (Vite 개발 서버)

### 프론트엔드 (React/TypeScript)
- TypeScript 사용 (strict mode)
- 컴포넌트 파일명: PascalCase (`FileCard.tsx`)
- 훅 파일명: camelCase, use 접두사 (`useFiles.ts`)
- API 호출은 반드시 `src/api/` 디렉토리의 함수를 통해서만
- 모든 API 응답 타입은 `src/types/` 에 정의
- shadcn/ui 컴포넌트 커스터마이징 시 `src/components/ui/` 직접 수정
- 환경변수: `VITE_API_BASE_URL=http://localhost:8000` (`.env.local`)

---

## 파일 구조

```
data_warehouse/
├── CLAUDE.md
├── .env                          # ANTHROPIC_API_KEY
├── backend/
│   ├── main.py                   # FastAPI 앱, 라우터 등록, CORS 설정
│   ├── db.py                     # SQLite 연결 contextmanager, 초기화
│   ├── schemas.py                # Pydantic 모델
│   ├── file_handler.py           # 파일 읽기/저장/변환 유틸
│   ├── llm_service.py            # Anthropic API 호출 전담
│   ├── routers/
│   │   ├── upload.py             # POST /upload, /upload/confirm, /upload/merge
│   │   ├── files.py              # GET /files, /files/{id}/preview, /files/{id}/download
│   │   ├── query.py              # POST /query (자연어 검색)
│   │   ├── combine.py            # POST /combine, /combine/save
│   │   ├── lineage.py            # GET /lineage/graph (노드·엣지 JSON)
│   │   └── convention.py         # GET/POST /convention, /convention/suggest-rename
│   └── utils/
│       └── range_detector.py     # 날짜/키 범위 감지 로직
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── components.json           # shadcn/ui 설정
│   ├── .env.local                # VITE_API_BASE_URL
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               # 라우터 설정
│       ├── api/
│       │   ├── client.ts         # axios 인스턴스
│       │   ├── files.ts          # 파일 관련 API 함수
│       │   ├── upload.ts         # 업로드 관련 API 함수
│       │   ├── query.ts          # 검색 API 함수
│       │   ├── combine.ts        # 결합 API 함수
│       │   ├── lineage.ts        # Lineage API 함수
│       │   └── convention.ts     # 컨벤션 API 함수
│       ├── types/
│       │   └── index.ts          # 모든 타입 정의
│       ├── hooks/
│       │   ├── useFiles.ts       # TanStack Query 훅
│       │   ├── useUpload.ts
│       │   ├── useCombine.ts
│       │   └── useLineage.ts
│       ├── store/
│       │   └── ui.ts             # Zustand: 선택된 파일, 사이드바 상태 등
│       ├── components/
│       │   ├── ui/               # shadcn/ui 컴포넌트 (자동 생성)
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx   # 필터 사이드바
│       │   │   └── Header.tsx    # 상단 네비게이션
│       │   ├── file/
│       │   │   ├── FileCard.tsx  # 파일 카드 컴포넌트
│       │   │   ├── FileTable.tsx # TanStack Table 미리보기
│       │   │   └── RangeBar.tsx  # 날짜 범위 시각화 바
│       │   ├── upload/
│       │   │   ├── DropZone.tsx  # 드래그앤드롭 업로드 영역
│       │   │   ├── MetaForm.tsx  # LLM 분석 결과 편집 폼
│       │   │   └── MergeDialog.tsx # 겹침 감지 시 병합 정책 선택 다이얼로그
│       │   ├── combine/
│       │   │   ├── FileSelector.tsx  # 결합할 파일 선택
│       │   │   ├── CodePreview.tsx   # 생성된 pandas 코드 표시
│       │   │   └── ResultPreview.tsx # 결합 결과 미리보기
│       │   └── lineage/
│       │       └── LineageGraph.tsx  # React Flow 그래프
│       └── pages/
│           ├── Vault.tsx         # 📁 파일 창고
│           ├── Upload.tsx        # ⬆️ 업로드
│           ├── Search.tsx        # 🔍 검색
│           ├── Combine.tsx       # 🔗 결합
│           ├── Lineage.tsx       # 🕸️ Lineage
│           └── Convention.tsx    # ⚙️ 컨벤션 설정
├── requirements.txt
└── storage/                      # 실제 파일 저장 디렉토리 (자동 생성)
├── warehouse.db                  # SQLite DB (자동 생성)
└── temp/                         # 병합 결과 임시 파일 (자동 생성)
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
    output_id TEXT NOT NULL,              -- 결과 파일 ID (files 테이블 참조)
    operation TEXT NOT NULL,              -- 'concat' | 'merge' | 'smart_merge' | 'filter'
    operation_detail TEXT,                -- JSON: pandas 코드, merge 키, 병합 정책 등
    created_at TEXT NOT NULL
);
```

### naming_convention 테이블

```sql
CREATE TABLE IF NOT EXISTS naming_convention (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field TEXT NOT NULL,                  -- 'domain' | 'data_type' | 'stage' | 'tag'
    value TEXT NOT NULL,                  -- 예: 'PR', 'raw', 'ArF', 'pt75'
    description TEXT,                     -- 한국어 설명
    created_at TEXT NOT NULL
);
```

**field 종류 및 용도:**

| field | 용도 | 파일명 반영 | 예시 |
|---|---|---|---|
| `domain` | 공정/재료 도메인 | ✅ 파일명에 포함 | PR, WFR, IQC, CDA, PQC |
| `data_type` | 데이터 종류 | ✅ 파일명에 포함 | raw_iqc, coa, slope, doe, pqc |
| `stage` | 처리 단계 | ✅ 파일명에 포함 | raw, cleaned, merged, modeled, report |
| `tag` | 세부 속성 | ❌ 태그로만 사용 | ArF, KrF, pt25, pt75, Line1, MES, PI, vendor_A |

**파일명 구조:** `{domain}_{data_type}_{stage}_v{version}`
예: `PR_raw_iqc_v1`, `WFR_cleaned_outlier_v2`

**태그:** 파일명에 넣기엔 너무 세부적인 정보는 전부 tag로 관리
예: `["ArF", "pt75", "Line1", "MES"]`

---

## TypeScript 타입 정의 (`src/types/index.ts`)

```typescript
export interface FileRecord {
  id: string;
  original_filename: string;
  standardized_name: string;
  storage_path: string;
  category: string | null;
  project: string | null;
  description: string | null;
  tags: string[];           // JSON 파싱 후
  columns_info: Record<string, string>; // JSON 파싱 후
  row_count: number;
  range_column: string | null;
  range_min: string | null;
  range_max: string | null;
  range_type: 'date' | 'string' | 'numeric' | null;
  version: number;
  file_format: string;
  uploaded_at: string;
}

export interface UploadAnalysis {
  standardized_name: string;
  category: string;
  project: string;
  description: string;
  tags: string[];
  range_column: string | null;
  range_type: string | null;
  uncertain: boolean;
  question_for_user: string | null;
}

export interface OverlapInfo {
  overlap_detected: boolean;
  existing_file: { id: string; name: string; range: [string, string] } | null;
  new_file_range: [string, string] | null;
  overlap_range: [string, string] | null;
  overlap_row_estimate: number;
  merge_options: { key: string; label: string }[];
}

export interface LineageNode {
  id: string;
  data: {
    label: string;
    range: string;
    row_count: number;
    file_format: string;
    stage: 'raw' | 'merged' | 'modeled';
  };
  position: { x: number; y: number };
}

export interface LineageEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface CombineResult {
  code: string;
  preview: Record<string, unknown>[];
  row_count: number;
  col_count: number;
  temp_path: string;
}

export interface ConventionItem {
  id: number;
  field: 'domain' | 'data_type' | 'stage' | 'tag';
  value: string;
  description: string | null;
  created_at: string;
}
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

**프론트엔드 처리 (`MergeDialog.tsx`):**
- 업로드 후 overlap_detected가 true이면 자동으로 Dialog 오픈
- 범위 시각화: 두 파일의 범위를 가로 바 차트로 겹침 구간 강조 표시
- 병합 정책 RadioGroup으로 선택
- 확인 시 `POST /upload/merge` 호출

---

### 3. 네이밍 표준화 관리 (`GET/POST /convention`)

- 사용자가 도메인·데이터종류·처리단계 목록을 직접 정의
- LLM이 파일 분석할 때마다 이 목록을 컨텍스트로 전달
- **소급 정리 제안**: `POST /convention/suggest-rename` → 기존 파일 전체를 보고 컨벤션 불일치 파일명 + 제안 이름 반환. 사용자 체크박스로 선택 후 일괄 적용.

---

### 4. 파일 미리보기 (`GET /files/{id}/preview`)

- 포맷별 읽기: `pd.read_pickle`, `pd.read_csv`, `pd.read_parquet`, `pd.read_excel`
- 최대 100행, JSON 직렬화 (`orient="records"`)
- `range_column`이 있으면 해당 컬럼 기준 정렬 후 반환
- null/NaN은 `null`로 직렬화
- 프론트엔드: TanStack Table로 렌더링, 컬럼 정렬·고정 지원

---

### 5. 자연어 검색 (`POST /query`)

**LLM 프롬프트 구성:**
- 컨텍스트: 전체 파일의 `standardized_name`, `description`, `tags`, `range_min/max`, `project` 목록
- 사용자 질의 포함
- 응답 형식: 관련 파일 ID 목록 + 각 파일에 대한 한국어 설명 + 추천 이유

**프론트엔드 처리:**
- Command 팔레트 스타일 검색창 (⌘K 단축키)
- 검색 결과는 FileCard 컴포넌트 재사용해서 표시
- LLM 답변 텍스트는 결과 상단에 별도 표시

---

### 6. 자연어 Concat/Join (`POST /combine`)

**처리 흐름:**
1. 파일 ID 목록 + 자연어 명령 수신
2. 각 파일의 `columns_info` + `range_column` + 명령을 LLM에 전달
3. LLM이 pandas 코드 생성 (변수명 규칙: 입력은 `df_0`, `df_1`, ... / 결과는 반드시 `result_df`)
4. 코드 보안 검사 후 샌드박스 실행
5. 결과를 `temp/`에 저장, 다운로드 URL 반환
6. 사용자가 결과 저장 확정 시 → `POST /combine/save` → files + lineage 테이블에 정식 저장

**응답에 반드시 포함:**
- 생성된 pandas 코드 (CodePreview 컴포넌트로 표시, syntax highlighting)
- 결과 미리보기 (상위 20행, TanStack Table)
- 결과 행/열 수

---

### 7. Lineage Graph (`GET /lineage/graph`)

**백엔드:**
- `lineage` 테이블 조회 후 React Flow 호환 형식으로 반환
- 노드 위치는 백엔드에서 계산 (레이어별 x, y 좌표)
- 노드 `stage` 분류: standardized_name에 'raw' 포함 → raw, 'merged'/'concat' 포함 → merged, 나머지 → modeled

**응답 형식:**
```json
{
  "nodes": [
    {
      "id": "abc12345",
      "data": {"label": "PR_raw_iqc_v1", "range": "03/13~06/18", "row_count": 12430, "file_format": "pkl", "stage": "raw"},
      "position": {"x": 100, "y": 50}
    }
  ],
  "edges": [
    {"id": "e1", "source": "abc12345", "target": "def67890", "label": "smart_merge"}
  ]
}
```

**프론트엔드 (`LineageGraph.tsx`):**
- React Flow로 인터랙티브 그래프 렌더링
- 노드 색상: raw=파란색, merged=초록색, modeled=주황색
- 노드 클릭 시 우측 Sheet 컴포넌트에 파일 메타데이터 표시
- 미니맵, 줌 컨트롤 포함

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
| GET | `/lineage/graph` | React Flow 호환 노드·엣지 JSON |
| GET | `/convention` | 네이밍 컨벤션 목록 |
| POST | `/convention` | 컨벤션 항목 추가 |
| POST | `/convention/suggest-rename` | 기존 파일 소급 정리 제안 |

---

## 디자인 시스템

### 레퍼런스
Linear + Vercel 스타일. 좌측 고정 사이드바 + 우측 리스트 뷰. 군더더기 없이 깔끔하고 정보 밀도 높은 개발 도구 느낌.

### 레이아웃 구조
```
┌─────────────────────────────────────────────┐
│  Header (48px) — 검색창(⌘K) + 업로드 버튼   │
├──────────────┬──────────────────────────────┤
│              │                              │
│  Sidebar     │  Main Content               │
│  (220px)     │                              │
│              │                              │
│  - 네비게이션 │                              │
│  - 카테고리  │                              │
│    필터      │                              │
│              │                              │
└──────────────┴──────────────────────────────┘
```

### 컬러 팔레트
shadcn/ui 기본 테마(zinc) 사용. 커스텀 컬러 최소화.
카테고리 뱃지 색상만 고정:
- PR: 보라 계열 (`bg-violet-100 text-violet-800`)
- WFR: 초록 계열 (`bg-emerald-100 text-emerald-800`)
- IQC: 주황 계열 (`bg-amber-100 text-amber-800`)
- CDA: 파랑 계열 (`bg-blue-100 text-blue-800`)
- 기타: 회색 (`bg-zinc-100 text-zinc-600`)

### Lineage 노드 색상
- raw: 파랑 (`#378ADD`)
- merged: 초록 (`#1D9E75`)
- modeled: 주황 (`#BA7517`)

### 타이포그래피
- 페이지 타이틀: 16px / font-medium
- 리스트 항목 이름: 14px / font-medium
- 메타 정보(행수·날짜): 12px / text-muted-foreground
- 뱃지: 11px

### 핵심 컴포넌트 스펙

**사이드바 (`Sidebar.tsx`)**
- 상단: 앱 로고/이름
- 네비게이션 항목: 아이콘 + 텍스트, hover 시 bg-accent
- 활성 항목: bg-accent + font-medium
- 구분선 아래: 카테고리별 필터 (Checkbox)
- 하단 고정: 컨벤션 설정, 다크모드 토글

**파일 리스트 행 (`FileRow.tsx`)**
- 좌측: 컬러 닷(category 색상) + 파일명(font-medium) + 포맷 뱃지
- 중앙: 행수 뱃지, 날짜 범위
- 우측: 액션 버튼들 (hover 시 표시)
- 클릭 시 우측 Sheet 슬라이드인으로 상세 정보 표시

**빈 상태 (파일 없을 때)**
- 중앙 정렬, 아이콘 + "파일을 업로드해 창고를 채워보세요" 텍스트
- [첫 파일 업로드하기] 버튼

### 다크모드
shadcn/ui 기본 다크모드 지원. `next-themes` 대신 `class` 방식으로 토글.

---

## React 페이지 및 컴포넌트 명세

### 레이아웃
- 좌측 고정 사이드바 (240px): 네비게이션 + 필터
- 우측 메인 영역: 페이지 컨텐츠
- 상단 Header: 검색창 (⌘K), 업로드 버튼

### 📁 Vault.tsx (파일 창고)
- 사이드바 필터: category / project / tag (Checkbox 다중 선택)
- 파일 카드 그리드 (2열): FileCard 컴포넌트
- FileCard 내용:
  - 상단: standardized_name (굵게) + file_format 뱃지 + category 뱃지
  - 중간: description (2줄 말줄임), tags (작은 뱃지들)
  - RangeBar: range_min~max 시각화 (파일의 전체 날짜 범위 대비 위치)
  - 하단: row_count×col_count, 업로드 날짜
  - 액션: [미리보기] [CSV] [PKL] [결합에 추가]
- 미리보기 클릭 시 Sheet(drawer)가 우측에서 슬라이드인, TanStack Table 표시

### ⬆️ Upload.tsx (업로드)
- DropZone: 드래그앤드롭 + 클릭 업로드, 다중 파일 지원
- 업로드 후 분석 중 Skeleton 표시
- MetaForm: LLM 분석 결과를 편집 가능한 폼으로 표시
  - uncertain: true 시 Alert 컴포넌트로 LLM 질문 표시 + 답변 Input
- MergeDialog: overlap_detected 시 자동 오픈
  - 범위 겹침 시각화 바 포함
  - RadioGroup으로 병합 정책 선택
- [저장 확정] Button

### 🔍 Search.tsx (검색)
- 상단 큰 검색 Input (엔터로 검색)
- LLM 답변: 결과 상단 Card에 텍스트로 표시
- 관련 파일: FileCard 컴포넌트 재사용

### 🔗 Combine.tsx (결합)
- 좌측: 파일 목록 (Checkbox로 선택, 최소 2개)
- 선택된 파일들의 columns_info 나란히 표시 (ScrollArea)
- 자연어 명령 Textarea
- [코드 생성] → CodePreview (syntax highlighting, 복사 버튼)
- [실행] → ResultPreview (TanStack Table 미리보기, 행·열 수 표시)
- [창고에 저장] + [다운로드 CSV/PKL]

### 🕸️ Lineage.tsx (Lineage)
- React Flow 전체 화면
- 노드 클릭 시 우측 Sheet에 FileCard 표시
- 상단 툴바: 줌인/아웃, 전체 보기, 미니맵 토글

### ⚙️ Convention.tsx (컨벤션 설정)
- 탭 3개: domain / data_type / stage
- 각 탭: 현재 값 목록 (삭제 가능) + 새 항목 추가 폼
- [소급 정리 제안] Button → 결과를 Dialog로 표시
  - 변경 전/후 파일명 나란히 표시
  - Checkbox로 선택 후 [선택 항목 적용]

---

## LLM 프롬프트 설계 원칙

### 공통
- 모든 LLM 응답은 JSON only 강제: `"반드시 JSON만 반환하고 마크다운 코드블록이나 다른 텍스트는 포함하지 마라"`
- 응답 파싱 실패 시 3회 retry 후 에러 반환

### 파일 분석 프롬프트 (`analyze_file`)
```
컨텍스트:
- 파일명용 컨벤션 (domain / data_type / stage): {field IN ('domain','data_type','stage') 목록}
- 태그용 컨벤션 (tag): {field = 'tag' 목록}
- 기존 파일 목록: {standardized_name 리스트}
- 신규 파일 샘플: 컬럼명={columns}, 상위5행={sample_rows}

지시:
1. standardized_name은 반드시 domain/data_type/stage 목록에서만 골라 조합하라.
2. tags는 반드시 tag 목록에서만 골라 배열로 반환하라.
   - 목록에 없는 값은 절대 임의로 만들지 말 것.
   - 적절한 tag가 목록에 없으면 uncertain: true로 처리하고
     question_for_user에 "어떤 원료/라인/측정 조건인지" 구체적으로 질문하라.
3. uncertain이 false여도 태그 후보가 불확실하면 question_for_user에 확인 질문 포함.
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

### Phase 1 — 프로젝트 초기화 + 핵심 창고
- 백엔드: `db.py`, `file_handler.py`, `llm_service.py` 구현
- 백엔드: `/upload`, `/upload/confirm`, `/files` 엔드포인트
- 프론트엔드 초기화:
  ```bash
  cd frontend
  npm create vite@latest . -- --template react-ts
  npm install
  npx shadcn@latest init
  npx shadcn@latest add card badge button sheet table input textarea dialog radio-group checkbox scroll-area skeleton alert tabs
  npm install axios @tanstack/react-query zustand
  ```
- 프론트엔드: `Vault.tsx`, `Upload.tsx`, `FileCard.tsx`, `MetaForm.tsx`

### Phase 2 — 네이밍 표준화
- 백엔드: `naming_convention` 테이블 + `/convention` 엔드포인트
- LLM 분석 프롬프트에 컨벤션 컨텍스트 주입
- 프론트엔드: `Convention.tsx`

### Phase 3 — 스마트 병합
- 백엔드: `range_detector.py` + `/upload/merge` 엔드포인트
- 프론트엔드: `MergeDialog.tsx` (범위 시각화 포함), `RangeBar.tsx`

### Phase 4 — 자연어 기능
- 백엔드: `/query`, `/combine`, `/combine/save` 엔드포인트
- 프론트엔드: `Search.tsx`, `Combine.tsx`, `CodePreview.tsx`, `ResultPreview.tsx`

### Phase 5 — Lineage Graph
- 백엔드: `/lineage/graph` 엔드포인트 (React Flow 형식 반환)
- 프론트엔드:
  ```bash
  npm install @xyflow/react
  ```
- 프론트엔드: `LineageGraph.tsx`, `Lineage.tsx`

---

## 실행 방법

### 개발 환경 (개인 노트북)

```bash
# 백엔드
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

개발 중에는 Vite 개발 서버(5173)와 FastAPI(8000)가 분리되어 실행된다.
`vite.config.ts`에 프록시 설정을 추가해 CORS 없이 API 호출되도록 한다:

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'  // /api/* → FastAPI로 프록시
    }
  }
})
```

백엔드 라우터는 모두 `/api` 접두사 붙일 것 (예: `/api/files`, `/api/upload`).

---

### 사내 서버 배포

**노트북에서 빌드:**
```bash
cd frontend
npm run build
# → frontend/dist/ 폴더 생성됨
```

**서버에 올릴 파일 목록:**
```
backend/          # Python 소스 전체
dist/             # React 빌드 결과물 (node_modules 불필요)
requirements.txt
.env
storage/          # 기존 데이터 파일 (있는 경우)
warehouse.db      # 기존 DB (있는 경우)
```

**`main.py`에 정적 파일 서빙 설정 포함할 것:**
```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# API 라우터 등록 후 맨 마지막에 추가
dist_path = Path(__file__).parent.parent / "dist"
if dist_path.exists():
    # React 빌드 파일 서빙 (SPA 라우팅 지원)
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static")
```

**서버 실행:**
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
# → http://{서버IP}:8000 하나로 프론트 + 백엔드 동시 서빙
```

---

## requirements.txt (백엔드)

```
fastapi
uvicorn[standard]
anthropic
pandas
numpy
pyarrow
openpyxl
python-multipart
aiofiles
python-dotenv
pydantic
```