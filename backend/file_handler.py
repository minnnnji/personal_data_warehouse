import pickle
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

STORAGE_DIR = Path(__file__).parent.parent / "storage"
TEMP_DIR = STORAGE_DIR / "temp"


def ensure_dirs():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def _find_all_dataframes(obj: Any, path: str = "root", depth: int = 0) -> List[Tuple[str, pd.DataFrame]]:
    """pkl 객체에서 모든 DataFrame을 (경로, df) 리스트로 재귀 탐색 (최대 5단계)."""
    if depth > 5:
        return []
    if isinstance(obj, pd.DataFrame):
        return [(path, obj)]
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            results.extend(_find_all_dataframes(v, f"{path}['{k}']", depth + 1))
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            results.extend(_find_all_dataframes(item, f"{path}[{i}]", depth + 1))
    return results


def _load_raw(file_path: str, pkl_key: Optional[str] = None) -> pd.DataFrame:
    """원본 포맷 파일을 DataFrame으로 읽기."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="cp949")
    elif suffix == ".pkl":
        with open(path, "rb") as f:
            obj = pickle.load(f)
        if isinstance(obj, pd.DataFrame):
            return obj
        all_dfs = _find_all_dataframes(obj)
        if not all_dfs:
            obj_desc = f"타입={type(obj).__name__}"
            if isinstance(obj, dict):
                obj_desc += f", 최상위 키={list(obj.keys())}"
            raise ValueError(f"pkl 파일에 DataFrame이 없습니다. {obj_desc}")
        if pkl_key:
            matched = next((df for k, df in all_dfs if k == pkl_key), None)
            if matched is None:
                available = [k for k, _ in all_dfs]
                raise ValueError(f"pkl 키 '{pkl_key}'를 찾을 수 없습니다. 사용 가능: {available}")
            return matched
        return all_dfs[0][1]
    elif suffix == ".parquet":
        return pd.read_parquet(path)
    elif suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    elif suffix == ".json":
        return pd.read_json(path)
    else:
        raise ValueError(f"지원하지 않는 포맷: {suffix}")


def read_file(file_path: str, pkl_key: Optional[str] = None) -> pd.DataFrame:
    """저장된 파일(parquet 또는 레거시 포맷) 읽기."""
    return _load_raw(file_path, pkl_key=pkl_key)


def get_pkl_all_dataframes(file_path: str) -> List[Dict[str, Any]]:
    """pkl 파일에 존재하는 모든 DataFrame의 키·크기 목록 반환."""
    path = Path(file_path)
    with open(path, "rb") as f:
        obj = pickle.load(f)
    if isinstance(obj, pd.DataFrame):
        return [{"key": "root", "rows": len(obj), "cols": len(obj.columns)}]
    all_dfs = _find_all_dataframes(obj)
    return [
        {"key": k, "rows": len(df), "cols": len(df.columns)}
        for k, df in all_dfs
    ]


def get_pkl_dataframes_raw(file_path: str) -> List[Tuple[str, pd.DataFrame]]:
    """pkl 파일에서 (키, DataFrame) 전체 목록 반환."""
    path = Path(file_path)
    with open(path, "rb") as f:
        obj = pickle.load(f)
    if isinstance(obj, pd.DataFrame):
        return [("root", obj)]
    all_dfs = _find_all_dataframes(obj)
    if not all_dfs:
        raise ValueError("pkl 파일에 DataFrame이 없습니다.")
    return all_dfs


def get_sample_data(df: pd.DataFrame, n: int = 5) -> Dict[str, Any]:
    sample = df.head(n).copy()
    for col in sample.columns:
        sample[col] = sample[col].astype(str)

    columns_info = []
    for col in df.columns:
        columns_info.append(
            {
                "name": str(col),
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "sample_values": df[col].dropna().head(3).astype(str).tolist(),
            }
        )

    return {
        "columns": list(df.columns),
        "sample_rows": sample.to_dict(orient="records"),
        "columns_info": columns_info,
        "row_count": int(len(df)),
        "col_count": int(len(df.columns)),
    }


def save_as_parquet(df: pd.DataFrame, file_id: str) -> str:
    """DataFrame을 parquet으로 영구 저장 후 경로 반환."""
    ensure_dirs()
    output_path = STORAGE_DIR / f"{file_id}.parquet"
    df.to_parquet(output_path, index=False)
    return str(output_path)


def save_file_as_parquet(file_content: bytes, filename: str, file_id: str) -> Tuple[str, str, List[Tuple[str, pd.DataFrame]]]:
    """
    업로드 파일을 읽어 parquet으로 변환 저장.
    반환: (stored_path, original_format, [(pkl_key, df), ...])
    pkl이 아닌 경우 리스트는 단일 요소.
    """
    ensure_dirs()
    suffix = Path(filename).suffix.lower()
    original_format = suffix.lstrip(".")

    # 임시 파일에 원본 저장 후 읽기
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        if suffix == ".pkl":
            all_dfs = get_pkl_dataframes_raw(tmp_path)
        else:
            df = _load_raw(tmp_path)
            all_dfs = [("root", df)]
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # 단일 DataFrame이면 바로 저장
    if len(all_dfs) == 1:
        stored_path = save_as_parquet(all_dfs[0][1], file_id)
        return stored_path, original_format, all_dfs

    # 다중 DataFrame이면 첫 번째만 메인으로 저장 (나머지는 호출부에서 처리)
    stored_path = save_as_parquet(all_dfs[0][1], file_id)
    return stored_path, original_format, all_dfs


def convert_and_save(df: pd.DataFrame, file_id: str, target_format: str) -> str:
    ensure_dirs()
    output_path = TEMP_DIR / f"{file_id}_converted.{target_format}"
    if target_format == "csv":
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    elif target_format == "xlsx":
        df.to_excel(output_path, index=False)
    elif target_format == "pkl":
        with open(output_path, "wb") as f:
            pickle.dump(df, f)
    elif target_format == "parquet":
        df.to_parquet(output_path, index=False)
    else:
        raise ValueError(f"지원하지 않는 변환 포맷: {target_format}")
    return str(output_path)


def save_result_df(df: pd.DataFrame, result_id: str) -> str:
    ensure_dirs()
    output_path = TEMP_DIR / f"{result_id}.pkl"
    with open(output_path, "wb") as f:
        pickle.dump(df, f)
    return str(output_path)
