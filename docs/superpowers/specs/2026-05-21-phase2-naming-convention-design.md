# Phase 2 설계 스펙 — DataFrame 저장 방식 통일 + 네이밍 컨벤션

**날짜:** 2026-05-21  
**범위:** DataFrame-level storage 통일, naming_convention 관리, standardized_name/product_name 필드 추가, UI 개선

---

## 1. 스토리지 레이어

### 핵심 원칙
업로드된 모든 파일은 내부적으로 **parquet 단일 포맷**으로 저장한다. 원본 포맷 정보는 DB의 `file_format` 컬럼에 기록한다.

### 업로드 흐름
```
파일 수신
  → 임시 파일로 저장 (원본 포맷)
  → DataFrame으로 읽기
  → parquet으로 변환 저장 (storage/{id}.parquet)
  → 임시 파일 삭제
  → LLM 분석
  → DB 등록
```

### pkl 다중 DataFrame 처리
- pkl 파일 안에 DataFrame이 N개 있을 경우: **자동으로 전체 분리 저장**
- 사용자 체크박스 선택 UI 제거
- 업로드 결과 화면에 "N개 DataFrame이 감지되어 모두 저장됩니다" 안내 표시
- 각 DataFrame은 별도 parquet 파일로 저장, DB에 별도 레코드로 등록
- `pkl_key` 컬럼은 유지 (어떤 키에서 추출됐는지 추적용)

### 기존 파일 호환
이미 저장된 파일은 원본 포맷 그대로 유지. `read_file()` 함수가 모든 포맷을 지원하므로 읽기 호환 유지됨.

---

## 2. DB 스키마

### files 테이블 — 신규 컬럼

```sql
ALTER TABLE files ADD COLUMN standardized_name TEXT DEFAULT NULL;
ALTER TABLE files ADD COLUMN product_name TEXT DEFAULT NULL;
```

| 컬럼 | 설명 |
|---|---|
| `standardized_name` | LLM이 네이밍 컨벤션 기반으로 생성. 예: `PR_A제품_raw_iqc_v1` |
| `product_name` | LLM이 파일에서 자동 감지. 업로드 확정 폼에서 사용자 수정 가능 |

기존 레코드는 NULL로 유지 (소급 적용 없음).

### naming_convention 테이블 (신규)

```sql
CREATE TABLE IF NOT EXISTS naming_convention (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field TEXT NOT NULL,       -- 'domain' | 'data_type' | 'stage'
    value TEXT NOT NULL,       -- 예: 'PR', 'raw', 'cleaned'
    description TEXT,
    created_at TEXT NOT NULL
);
```

### DB 접근 패턴

기존 `get_conn()` 직접 노출 방식을 contextmanager 패턴으로 교체:

```python
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
```

모든 DB 함수는 `with get_db() as conn:` 패턴으로 통일.

---

## 3. 백엔드 API

### 업로드 엔드포인트 변경

**`POST /upload`**
- 수신한 파일을 임시 저장 후 DataFrame으로 읽어 parquet 변환 저장
- pkl 다중 DataFrame: 자동 전체 분리 (첫 번째 DataFrame으로 LLM 분석)
- 응답에서 `pkl_dataframes` 제거 (선택 UI 폐기)
- 응답에 `pkl_count` 추가 (감지된 DataFrame 수 안내용)

**`POST /upload/confirm`**
- pkl 분기 로직 제거 (이미 parquet 분리 완료)
- `standardized_name`, `product_name` 필드 DB 저장

### 신규 `/convention` 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/convention` | 전체 컨벤션 목록 반환 |
| POST | `/convention` | 항목 추가 |
| DELETE | `/convention/{id}` | 항목 삭제 |

응답 형식 (`GET /convention`):
```json
{
  "domain": [{"id": 1, "value": "PR", "description": "포토레지스트"}],
  "data_type": [{"id": 2, "value": "raw", "description": "원천 데이터"}],
  "stage": [{"id": 3, "value": "cleaned", "description": "전처리 완료"}]
}
```

### LLM 분석 변경 (`generate_metadata`)

프롬프트에 추가 컨텍스트 주입:
- 현재 `naming_convention` 테이블 전체
- 기존 파일의 `standardized_name` 목록

LLM 응답 스키마:
```json
{
  "standardized_name": "PR_A제품_raw_iqc_v1",
  "product_name": "A제품",
  "description": "...",
  "category": "품질",
  "tags": ["lot_id", "iqc"],
  "project_guess": "",
  "uncertain": false,
  "question_for_user": null
}
```

`standardized_name` 생성 규칙 (프롬프트에 명시):
```
{domain}_{product_name}_{data_type}_{stage}_v1
예) PR_A제품_raw_iqc_v1
```

---

## 4. Streamlit UI

UI 설계 원칙 (design.md 참조): 불필요한 장식 제거, 충분한 여백, 단일 강조색, 정보는 제품이 말하게.

### 파일 창고 탭 — 카드 변경

```
[표준화 이름]                   [원본: original_filename]
 카테고리 | 프로젝트 | 제품명
 행×열   `태그1` `태그2`
                               [👁] [⬇] [⋮]
```

- `standardized_name`을 주 식별자로 표시 (NULL이면 `original_filename` 폴백)
- 원본 파일명은 작게 보조 표시
- 제품명(`product_name`) 메타 라인에 추가

### 업로드 탭 — 확정 폼 변경

```
[표준화 이름]       [제품명]
[카테고리]          [프로젝트명]
[설명]
[태그]
```

- pkl 다중 DataFrame: 체크박스 제거 → "📦 DataFrame N개 감지 — 모두 저장됩니다" 안내 배너
- `standardized_name` 필드: LLM 생성값 프리필, 사용자 수정 가능
- `product_name` 필드: LLM 감지값 프리필, 사용자 수정 가능

### 신규 ⚙️ 컨벤션 설정 탭

```
Domain          Data Type       Stage
─────────────   ─────────────   ─────────────
PR  포토레지…  raw  원천 데…   cleaned  전처리…
WFR 웨이퍼…    model 모델링…   report   보고서…
[+ 추가]       [+ 추가]        [+ 추가]

각 행에 [🗑 삭제] 버튼
```

- field 타입별 3컬럼 레이아웃
- 항목 추가 폼: field 선택(domain/data_type/stage) + value + description
- 삭제는 즉시 반영

### 탭 구성 변경

```
[📁 파일 창고]  [⬆️ 업로드]  [🔍 검색]  [🔗 결합]  [⚙️ 컨벤션 설정]
```

---

## 5. 변경 파일 요약

| 파일 | 변경 유형 | 주요 내용 |
|---|---|---|
| `backend/db.py` | 수정 | contextmanager 패턴, `standardized_name`/`product_name` 컬럼 마이그레이션, naming_convention CRUD |
| `backend/schemas.py` | 수정 | `ConfirmUploadRequest`에 `standardized_name`, `product_name` 추가 |
| `backend/file_handler.py` | 수정 | `save_file()` → parquet 변환 저장, `save_as_parquet()` 추가 |
| `backend/llm_service.py` | 수정 | `generate_metadata()` 컨벤션 컨텍스트 주입, `product_name`/`standardized_name` 생성 |
| `backend/main.py` | 수정 | 업로드 플로우 변경(parquet), pkl 자동 분리, `/convention` 엔드포인트 추가 |
| `frontend/app.py` | 수정 | 파일 카드 업데이트, 업로드 폼 업데이트, 컨벤션 탭 추가 |
