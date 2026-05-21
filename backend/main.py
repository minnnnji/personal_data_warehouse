import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.db import (
    add_convention,
    delete_convention,
    delete_file_record,
    get_all_files,
    get_all_lineage,
    get_all_standardized_names,
    get_all_tags,
    get_conventions,
    get_conventions_flat,
    get_distinct_categories,
    get_distinct_projects,
    get_file_by_id,
    init_db,
    save_file_metadata,
    save_lineage,
    update_file_metadata,
)
from backend.file_handler import (
    TEMP_DIR,
    convert_and_save,
    get_sample_data,
    read_file,
    save_as_parquet,
    save_file_as_parquet,
    save_result_df,
)
from backend.llm_service import generate_combine_code, generate_metadata, search_files
from backend.schemas import (
    CombineRequest,
    ConfirmUploadRequest,
    ConventionAddRequest,
    QueryRequest,
)

import json
import pickle

load_dotenv()

app = FastAPI(title="Personal Data Warehouse API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모든 API 라우트를 /api 하위에 마운트하기 위한 서브 앱
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

# 업로드 확정 전 임시 저장 (프로세스 메모리)
_pending: dict = {}

FORBIDDEN_PATTERNS = [
    "import", "os.", "sys.", "open(", "eval(", "exec(",
    "__import__", "__builtins__", "subprocess", "shutil", "pathlib",
]


@app.on_event("startup")
def startup():
    init_db()
    (Path(__file__).parent.parent / "storage").mkdir(parents=True, exist_ok=True)
    (Path(__file__).parent.parent / "storage" / "temp").mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# 파일 업로드
# ──────────────────────────────────────────────────────────────────────────────


@api_router.post("/upload", summary="파일 업로드 + LLM 메타데이터 자동 생성")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    file_id = str(uuid.uuid4())[:8]

    # 1. 파일 읽기 → parquet 변환 저장 (pkl은 다중 DataFrame 자동 분리)
    try:
        stored_path, original_format, all_dfs = save_file_as_parquet(
            content, file.filename, file_id
        )
    except Exception as e:
        raise HTTPException(400, f"파일 파싱/저장 실패: {e}")

    pkl_count = len(all_dfs) if file.filename.lower().endswith(".pkl") and len(all_dfs) > 1 else None

    # 2. 첫 번째 DataFrame으로 샘플 추출
    try:
        sample = get_sample_data(all_dfs[0][1])
    except Exception as e:
        Path(stored_path).unlink(missing_ok=True)
        raise HTTPException(400, f"샘플 추출 실패: {e}")

    # 3. 컨벤션 컨텍스트 로드
    conventions = get_conventions()
    existing_names = get_all_standardized_names()

    # 4. LLM 메타데이터 생성
    try:
        llm = generate_metadata(
            sample["columns_info"],
            sample["sample_rows"],
            file.filename,
            conventions=conventions,
            existing_names=existing_names,
        )
    except Exception as e:
        llm = {
            "standardized_name": "",
            "product_name": "",
            "description": "",
            "category": "기타",
            "tags": [],
            "project_guess": "",
            "uncertain": True,
            "question_for_user": f"LLM 호출 오류: {e}. 직접 메타데이터를 입력해주세요.",
        }

    meta = {
        "id": file_id,
        "original_filename": file.filename,
        "stored_path": stored_path,
        "file_format": original_format,
        "category": llm.get("category", "기타"),
        "description": llm.get("description", ""),
        "tags": llm.get("tags", []),
        "columns_info": sample["columns_info"],
        "row_count": sample["row_count"],
        "col_count": sample["col_count"],
        "upload_date": datetime.now().isoformat(),
        "project_name": llm.get("project_guess", ""),
        "file_size": len(content),
        "standardized_name": llm.get("standardized_name", ""),
        "product_name": llm.get("product_name", ""),
        "pkl_key": all_dfs[0][0] if all_dfs[0][0] != "root" else None,
        # pkl 다중 DataFrame 정보 — confirm 시 나머지 저장에 사용
        "_extra_dfs": [(k, df) for k, df in all_dfs[1:]] if len(all_dfs) > 1 else [],
        # pkl 원본 stem 보존 — confirm 시 sub 파일명 생성용
        "_pkl_stem": Path(file.filename).stem if len(all_dfs) > 1 else None,
    }
    _pending[file_id] = meta

    return {
        "file_id": file_id,
        "metadata": {k: v for k, v in meta.items() if not k.startswith("_")},
        "uncertain": llm.get("uncertain", False),
        "question_for_user": llm.get("question_for_user") if llm.get("uncertain") else None,
        "pkl_count": pkl_count,
    }


@api_router.post("/upload/confirm", summary="메타데이터 확정 후 DB 저장")
def confirm_upload(req: ConfirmUploadRequest):
    if req.file_id not in _pending:
        raise HTTPException(404, "대기 중인 업로드를 찾을 수 없습니다 (이미 저장됐거나 만료)")
    meta = _pending.pop(req.file_id)
    extra_dfs = meta.pop("_extra_dfs", [])
    pkl_stem = meta.pop("_pkl_stem", None)

    final_sname = req.standardized_name or meta.get("standardized_name") or ""
    final_product = req.product_name or meta.get("product_name") or ""

    meta.update({
        "category": req.category,
        "description": req.description,
        "tags": req.tags,
        "project_name": req.project_name,
        "standardized_name": final_sname,
        "product_name": final_product,
    })

    # pkl 다중 DataFrame인 경우 첫 번째 df도 parquet 이름으로 통일
    if extra_dfs and pkl_stem:
        key0 = meta.get("pkl_key") or "root"
        parts0 = re.findall(r"'([^']+)'|\[(\d+)\]", key0) if key0 and key0 != "root" else []
        suffix0 = "_".join(p[0] or p[1] for p in parts0) or "df0"
        meta["original_filename"] = f"{pkl_stem}_{suffix0}.parquet"
        meta["file_format"] = "parquet"

    save_file_metadata(meta)

    # pkl 나머지 DataFrame — parquet 저장 + DB 등록
    saved_extra_ids = []
    if extra_dfs and pkl_stem:
        for pkl_key, df in extra_dfs:
            sub_id = str(uuid.uuid4())[:8]
            sub_path = save_as_parquet(df, sub_id)
            sub_sample = get_sample_data(df)

            parts = re.findall(r"'([^']+)'|\[(\d+)\]", pkl_key)
            suffix = "_".join(p[0] or p[1] for p in parts) or "df"

            # 메인 표준화 이름 기반으로 sub 표준화 이름 파생
            sub_sname = f"{final_sname}_{suffix}" if final_sname else None

            sub_meta = {
                "id": sub_id,
                "original_filename": f"{pkl_stem}_{suffix}.parquet",
                "stored_path": sub_path,
                "file_format": "parquet",
                "category": req.category,
                "description": req.description,
                "tags": req.tags,
                "project_name": req.project_name,
                "columns_info": sub_sample["columns_info"],
                "row_count": sub_sample["row_count"],
                "col_count": sub_sample["col_count"],
                "upload_date": meta["upload_date"],
                "file_size": Path(sub_path).stat().st_size,
                "pkl_key": pkl_key if pkl_key != "root" else None,
                "standardized_name": sub_sname,
                "product_name": final_product,
            }
            save_file_metadata(sub_meta)
            saved_extra_ids.append(sub_id)

    result: dict = {"success": True, "file_id": req.file_id}
    if saved_extra_ids:
        result["extra_file_ids"] = saved_extra_ids
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 파일 목록 / 상세 / 미리보기 / 다운로드 / 삭제
# ──────────────────────────────────────────────────────────────────────────────


@api_router.get("/files", summary="파일 목록 조회 (필터 지원)")
def list_files(
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
):
    return get_all_files(category=category, tag=tag, project=project)


@api_router.get("/files/{file_id}", summary="파일 메타데이터 상세 조회")
def get_file(file_id: str):
    f = get_file_by_id(file_id)
    if not f:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    return f


@api_router.put("/files/{file_id}", summary="파일 메타데이터 수정")
def update_file(file_id: str, req: ConfirmUploadRequest):
    f = get_file_by_id(file_id)
    if not f:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    update_file_metadata(
        file_id,
        {
            "category": req.category,
            "description": req.description,
            "tags": req.tags,
            "project_name": req.project_name,
            "standardized_name": req.standardized_name,
            "product_name": req.product_name,
        },
    )
    return {"success": True}


@api_router.patch("/files/{file_id}", summary="파일 메타데이터 부분 수정")
def patch_file(file_id: str, body: dict):
    f = get_file_by_id(file_id)
    if not f:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    allowed = {"category", "description", "tags", "project_name", "standardized_name", "product_name"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if updates:
        update_file_metadata(file_id, updates)
    return {"success": True}


@api_router.get("/files/{file_id}/preview", summary="파일 내용 테이블 미리보기 (최대 100행)")
def preview_file(file_id: str, limit: int = 100):
    f = get_file_by_id(file_id)
    if not f:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    try:
        df = read_file(f["stored_path"], pkl_key=f.get("pkl_key"))
        preview = df.head(limit).copy()
        for col in preview.columns:
            preview[col] = preview[col].astype(str)
        return {
            "columns": list(preview.columns),
            "data": preview.to_dict(orient="records"),
            "total_rows": int(len(df)),
            "preview_rows": int(len(preview)),
        }
    except Exception as e:
        raise HTTPException(500, f"미리보기 실패: {e}")


@api_router.get("/files/{file_id}/download", summary="파일 다운로드 (포맷 변환 지원)")
def download_file(file_id: str, format: str = Query("csv")):
    f = get_file_by_id(file_id)
    if not f:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    if format not in ("csv", "xlsx", "pkl", "parquet"):
        raise HTTPException(400, "지원 포맷: csv, xlsx, pkl, parquet")

    original_ext = Path(f["stored_path"]).suffix.lstrip(".")
    if original_ext == format:
        return FileResponse(
            f["stored_path"],
            filename=f["original_filename"],
            media_type="application/octet-stream",
        )
    try:
        df = read_file(f["stored_path"])
        out_path = convert_and_save(df, file_id, format)
        stem = Path(f["original_filename"]).stem
        return FileResponse(
            out_path,
            filename=f"{stem}.{format}",
            media_type="application/octet-stream",
        )
    except Exception as e:
        raise HTTPException(500, f"변환 실패: {e}")


@api_router.delete("/files/{file_id}", summary="파일 삭제 (파일 + DB 기록)")
def delete_file(file_id: str):
    f = get_file_by_id(file_id)
    if not f:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    Path(f["stored_path"]).unlink(missing_ok=True)
    delete_file_record(file_id)
    return {"success": True}


# ──────────────────────────────────────────────────────────────────────────────
# 자연어 검색
# ──────────────────────────────────────────────────────────────────────────────


@api_router.post("/query", summary="자연어로 파일 검색")
def query_files(req: QueryRequest):
    all_files = get_all_files()
    if not all_files:
        return {
            "answer": "아직 저장된 파일이 없습니다. 먼저 파일을 업로드해주세요.",
            "mentioned_file_ids": [],
            "all_files": [],
        }
    answer = search_files(req.query, all_files)
    mentioned = [
        f["id"]
        for f in all_files
        if f["id"] in answer
        or f["original_filename"] in answer
        or (f.get("standardized_name") and f["standardized_name"] in answer)
    ]
    return {"answer": answer, "mentioned_file_ids": mentioned, "all_files": all_files}


# ──────────────────────────────────────────────────────────────────────────────
# 자연어 데이터 결합
# ──────────────────────────────────────────────────────────────────────────────


@api_router.post("/combine", summary="자연어 명령으로 파일 결합 (LLM pandas 코드 생성)")
def combine_files(req: CombineRequest):
    if len(req.file_ids) < 1:
        raise HTTPException(400, "최소 1개 파일을 선택해야 합니다")

    files_meta = []
    for fid in req.file_ids:
        f = get_file_by_id(fid)
        if not f:
            raise HTTPException(404, f"파일 ID '{fid}'를 찾을 수 없습니다")
        files_meta.append(f)

    generated_code = generate_combine_code(files_meta, req.command)

    code_lower = generated_code.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in code_lower:
            raise HTTPException(
                400,
                f"보안 위반: 생성된 코드에 허용되지 않는 패턴 '{pattern}'이 포함되어 있습니다.\n\n코드:\n{generated_code}",
            )

    exec_ns: dict = {"pd": pd, "np": np}
    for i, meta in enumerate(files_meta):
        try:
            exec_ns[f"df_{i}"] = read_file(meta["stored_path"], pkl_key=meta.get("pkl_key"))
        except Exception as e:
            raise HTTPException(500, f"'{meta['original_filename']}' 로드 실패: {e}")

    try:
        exec(generated_code, exec_ns)  # noqa: S102
    except Exception as e:
        raise HTTPException(500, f"코드 실행 오류: {e}\n\n생성된 코드:\n{generated_code}")

    result_df = exec_ns.get("result_df")
    if result_df is None or not isinstance(result_df, pd.DataFrame):
        raise HTTPException(500, f"result_df가 정의되지 않았습니다.\n\n생성된 코드:\n{generated_code}")

    result_id = str(uuid.uuid4())
    save_result_df(result_df, result_id)

    preview_df = result_df.head(50).copy()
    for col in preview_df.columns:
        preview_df[col] = preview_df[col].astype(str)

    return {
        "generated_code": generated_code,
        "result_id": result_id,
        "preview": {
            "columns": list(preview_df.columns),
            "data": preview_df.to_dict(orient="records"),
        },
        "row_count": int(len(result_df)),
        "col_count": int(len(result_df.columns)),
    }


@api_router.post("/combine/save", summary="결합 결과를 창고에 저장")
def save_combine_result(req: dict):
    result_id = req.get("result_id")
    if not result_id:
        raise HTTPException(400, "result_id가 필요합니다")

    result_path = TEMP_DIR / f"{result_id}.pkl"
    if not result_path.exists():
        raise HTTPException(404, "결과 파일을 찾을 수 없습니다 (만료됐을 수 있음)")

    with open(result_path, "rb") as f:
        result_df = pickle.load(f)

    new_id = str(uuid.uuid4())[:8]
    stored_path = save_as_parquet(result_df, new_id)
    sample = get_sample_data(result_df)

    tags = req.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    meta = {
        "id": new_id,
        "original_filename": f"{req.get('standardized_name', 'combined')}.parquet",
        "stored_path": stored_path,
        "file_format": "parquet",
        "category": req.get("category", ""),
        "description": req.get("description", ""),
        "tags": tags,
        "columns_info": sample["columns_info"],
        "row_count": sample["row_count"],
        "col_count": sample["col_count"],
        "upload_date": datetime.now().isoformat(),
        "project_name": req.get("project_name", ""),
        "file_size": result_path.stat().st_size,
        "standardized_name": req.get("standardized_name", ""),
        "product_name": "",
    }
    save_file_metadata(meta)

    # lineage 기록
    lineage_record = {
        "id": str(uuid.uuid4())[:8],
        "source_ids": json.dumps(req.get("file_ids", []), ensure_ascii=False),
        "output_id": new_id,
        "operation": "combine",
        "operation_detail": req.get("code", ""),
        "created_at": datetime.now().isoformat(),
    }
    save_lineage(lineage_record)

    return get_file_by_id(new_id)


@api_router.get("/combine/{result_id}/download", summary="결합 결과 파일 다운로드")
def download_result(result_id: str, format: str = Query("csv")):
    result_path = TEMP_DIR / f"{result_id}.pkl"
    if not result_path.exists():
        raise HTTPException(404, "결과 파일을 찾을 수 없습니다 (만료됐을 수 있음)")
    if format not in ("csv", "xlsx", "pkl", "parquet"):
        raise HTTPException(400, "지원 포맷: csv, xlsx, pkl, parquet")
    with open(result_path, "rb") as f:
        result_df = pickle.load(f)
    out_path = convert_and_save(result_df, result_id, format)
    return FileResponse(
        out_path,
        filename=f"combined_result.{format}",
        media_type="application/octet-stream",
    )


# ──────────────────────────────────────────────────────────────────────────────
# 네이밍 컨벤션
# ──────────────────────────────────────────────────────────────────────────────


@api_router.get("/lineage", summary="데이터 계보 그래프 (JSON 노드+엣지)")
def get_lineage():
    records = get_all_lineage()
    all_file_ids: set = set()
    for r in records:
        srcs = json.loads(r["source_ids"])
        all_file_ids.update(srcs)
        all_file_ids.add(r["output_id"])

    nodes = []
    for fid in all_file_ids:
        f = get_file_by_id(fid)
        label = (f.get("standardized_name") or f.get("original_filename") or fid) if f else fid
        nodes.append({
            "id": fid,
            "label": label,
            "color": "#0066cc",
            "title": label,
        })

    edges = []
    for r in records:
        srcs = json.loads(r["source_ids"])
        for src in srcs:
            edges.append({
                "from": src,
                "to": r["output_id"],
                "label": r["operation"],
            })

    return {"nodes": nodes, "edges": edges}


@api_router.get("/convention", summary="네이밍 컨벤션 목록 (flat)")
def get_convention():
    return get_conventions_flat()


@api_router.post("/convention", summary="네이밍 컨벤션 항목 추가")
def add_convention_item(req: ConventionAddRequest):
    if req.field not in ("domain", "data_type", "stage"):
        raise HTTPException(400, "field는 domain, data_type, stage 중 하나여야 합니다")
    created_at = datetime.now().isoformat()
    new_id = add_convention(req.field, req.value, req.description or "", created_at)
    return {
        "id": new_id,
        "field": req.field,
        "value": req.value,
        "description": req.description or "",
        "created_at": created_at,
    }


@api_router.delete("/convention/{convention_id}", summary="네이밍 컨벤션 항목 삭제")
def delete_convention_item(convention_id: int):
    delete_convention(convention_id)
    return {"success": True}


# ──────────────────────────────────────────────────────────────────────────────
# 필터 옵션 (사이드바용)
# ──────────────────────────────────────────────────────────────────────────────


@api_router.get("/meta/categories")
def meta_categories():
    return get_distinct_categories()


@api_router.get("/meta/projects")
def meta_projects():
    return get_distinct_projects()


@api_router.get("/meta/tags")
def meta_tags():
    return get_all_tags()


# /api/* 라우터를 app에 등록
app.include_router(api_router)

# React 빌드 정적 파일 서빙 (API 라우터 등록 이후 맨 마지막에)
_dist = Path(__file__).parent.parent / "web" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
