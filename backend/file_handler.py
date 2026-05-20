import pickle
from pathlib import Path
from typing import Dict, Any, Tuple

import pandas as pd

STORAGE_DIR = Path(__file__).parent.parent / "storage"
TEMP_DIR = STORAGE_DIR / "temp"


def ensure_dirs():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def read_file(file_path: str) -> pd.DataFrame:
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
        raise ValueError("pkl 파일에 DataFrame이 없습니다")
    elif suffix == ".parquet":
        return pd.read_parquet(path)
    elif suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    elif suffix == ".json":
        return pd.read_json(path)
    else:
        raise ValueError(f"지원하지 않는 포맷: {suffix}")


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


def save_file(file_content: bytes, filename: str, file_id: str) -> Tuple[str, str]:
    ensure_dirs()
    suffix = Path(filename).suffix.lower()
    stored_path = STORAGE_DIR / f"{file_id}{suffix}"
    with open(stored_path, "wb") as f:
        f.write(file_content)
    return str(stored_path), suffix.lstrip(".")


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
