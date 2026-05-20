import os
import pickle
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

from backend.db import (
    delete_file_record,
    get_all_files,
    get_all_tags,
    get_distinct_categories,
    get_distinct_projects,
    get_file_by_id,
    init_db,
    save_file_metadata,
    update_file_metadata,
)
from backend.file_handler import (
    TEMP_DIR,
    convert_and_save,
    get_sample_data,
    read_file,
    save_file,
    save_result_df,
)
from backend.llm_service import generate_combine_code, generate_metadata, search_files
from backend.schemas import CombineRequest, ConfirmUploadRequest, QueryRequest

load_dotenv()

app = FastAPI(title="Personal Data Warehouse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드 확정 전 임시 저장 (프로세스 메모리)
_pending: dict = {}

# exec() 에서 허용하지 않는 패턴
FORBIDDEN_PATTERNS = [
    "import",
    "os.",
    "sys.",
    "open(",
    "eval(",
    "exec(",
    "__import__",
    "__builtins__",
    "subprocess",
    "shutil",
    "pathlib",
]


@app.on_event("startup")
def startup():
    init_db()
    (Path(__file__).parent.parent / "storage").mkdir(parents=True, exist_ok=True)
    (Path(__file__).parent.parent / "storage" / "temp").mkdir(
        parents=True, exist_ok=True
    )


# ──────────────────────────────────────────────────────────────────────────────
# 파일 업로드
# ──────────────────────────────────────────────────────────────────────────────


@app.post("/upload", summary="파일 업로드 + LLM 메타데이터 자동 생성")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    file_id = str(uuid.uuid4())

    # 1. 파일 저장
    try:
        stored_path, file_format = save_file(content, file.filename, file_id)
    except Exception as e:
        raise HTTPException(500, f"파일 저장 실패: {e}")

    # 2. 파일 읽기 + 샘플 추출
    try:
        df = read_file(stored_path)
        sample = get_sample_data(df)
    except Exception as e:
        Path(stored_path).unlink(missing_ok=True)
        raise HTTPException(400, f"파일 파싱 실패: {e}")

    # 3. LLM 메타데이터 생성
    try:
        llm = generate_metadata(
            sample["columns_info"], sample["sample_rows"], file.filename
        )
    except Exception as e:
        llm = {
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
        "file_format": file_format,
        "category": llm.get("category", "기타"),
        "description": llm.get("description", ""),
        "tags": llm.get("tags", []),
        "columns_info": sample["columns_info"],
        "row_count": sample["row_count"],
        "col_count": sample["col_count"],
        "upload_date": datetime.now().isoformat(),
        "project_name": llm.get("project_guess", ""),
        "file_size": len(content),
    }
    _pending[file_id] = meta

    return {
        "file_id": file_id,
        "metadata": meta,
        "uncertain": llm.get("uncertain", False),
        "question_for_user": llm.get("question_for_user") if llm.get("uncertain") else None,
    }


@app.post("/upload/confirm", summary="메타데이터 수정 확정 후 DB 저장")
def confirm_upload(req: ConfirmUploadRequest):
    if req.file_id not in _pending:
        raise HTTPException(404, "대기 중인 업로드를 찾을 수 없습니다 (이미 저장됐거나 만료)")
    meta = _pending.pop(req.file_id)
    meta["category"] = req.category
    meta["description"] = req.description
    meta["tags"] = req.tags
    meta["project_name"] = req.project_name
    save_file_metadata(meta)
    return {"success": True, "file_id": req.file_id}


# ──────────────────────────────────────────────────────────────────────────────
# 파일 목록 / 상세 / 미리보기 / 다운로드 / 삭제
# ──────────────────────────────────────────────────────────────────────────────


@app.get("/files", summary="파일 목록 조회 (필터 지원)")
def list_files(
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
):
    return get_all_files(category=category, tag=tag, project=project)


@app.get("/files/{file_id}", summary="파일 메타데이터 상세 조회")
def get_file(file_id: str):
    f = get_file_by_id(file_id)
    if not f:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    return f


@app.put("/files/{file_id}", summary="파일 메타데이터 수정")
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
        },
    )
    return {"success": True}


@app.get("/files/{file_id}/preview", summary="파일 내용 테이블 미리보기 (최대 100행)")
def preview_file(file_id: str, limit: int = 100):
    f = get_file_by_id(file_id)
    if not f:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    try:
        df = read_file(f["stored_path"])
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


@app.get("/files/{file_id}/download", summary="파일 다운로드 (포맷 변환 지원)")
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


@app.delete("/files/{file_id}", summary="파일 삭제 (파일 + DB 기록)")
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


@app.post("/query", summary="자연어로 파일 검색")
def query_files(req: QueryRequest):
    all_files = get_all_files()
    if not all_files:
        return {
            "answer": "아직 저장된 파일이 없습니다. 먼저 파일을 업로드해주세요.",
            "mentioned_file_ids": [],
            "all_files": [],
        }
    answer = search_files(req.query, all_files)
    # 응답에 언급된 파일 ID 추출 (파일명 또는 ID가 답변 텍스트에 포함된 경우)
    mentioned = [
        f["id"]
        for f in all_files
        if f["id"] in answer or f["original_filename"] in answer
    ]
    return {
        "answer": answer,
        "mentioned_file_ids": mentioned,
        "all_files": all_files,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 자연어 데이터 결합
# ──────────────────────────────────────────────────────────────────────────────


@app.post("/combine", summary="자연어 명령으로 파일 결합 (LLM pandas 코드 생성)")
def combine_files(req: CombineRequest):
    if len(req.file_ids) < 2:
        raise HTTPException(400, "최소 2개 파일을 선택해야 합니다")

    files_meta = []
    for fid in req.file_ids:
        f = get_file_by_id(fid)
        if not f:
            raise HTTPException(404, f"파일 ID '{fid}'를 찾을 수 없습니다")
        files_meta.append(f)

    # LLM 코드 생성
    generated_code = generate_combine_code(files_meta, req.command)

    # 보안 검사
    code_lower = generated_code.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in code_lower:
            raise HTTPException(
                400,
                f"보안 위반: 생성된 코드에 허용되지 않는 패턴 '{pattern}'이 포함되어 있습니다.\n\n코드:\n{generated_code}",
            )

    # 데이터프레임 로드
    exec_ns: dict = {"pd": pd, "np": np}
    for i, meta in enumerate(files_meta):
        try:
            exec_ns[f"df_{i}"] = read_file(meta["stored_path"])
        except Exception as e:
            raise HTTPException(
                500, f"'{meta['original_filename']}' 로드 실패: {e}"
            )

    # 코드 실행
    try:
        exec(generated_code, exec_ns)  # noqa: S102
    except Exception as e:
        raise HTTPException(
            500,
            f"코드 실행 오류: {e}\n\n생성된 코드:\n{generated_code}",
        )

    result_df = exec_ns.get("result_df")
    if result_df is None or not isinstance(result_df, pd.DataFrame):
        raise HTTPException(
            500,
            f"result_df가 정의되지 않았습니다.\n\n생성된 코드:\n{generated_code}",
        )

    # 결과 저장
    result_id = str(uuid.uuid4())
    save_result_df(result_df, result_id)

    # 미리보기 (50행, 문자열 변환)
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


@app.get("/combine/{result_id}/download", summary="결합 결과 파일 다운로드")
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
# 필터 옵션 (사이드바용)
# ──────────────────────────────────────────────────────────────────────────────


@app.get("/meta/categories")
def meta_categories():
    return get_distinct_categories()


@app.get("/meta/projects")
def meta_projects():
    return get_distinct_projects()


@app.get("/meta/tags")
def meta_tags():
    return get_all_tags()
