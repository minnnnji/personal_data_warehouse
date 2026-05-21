import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).parent.parent / "warehouse.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_format TEXT NOT NULL,
                category TEXT DEFAULT '',
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                columns_info TEXT DEFAULT '[]',
                row_count INTEGER DEFAULT 0,
                col_count INTEGER DEFAULT 0,
                upload_date TEXT NOT NULL,
                project_name TEXT DEFAULT '',
                file_size INTEGER DEFAULT 0,
                pkl_key TEXT DEFAULT NULL,
                standardized_name TEXT DEFAULT NULL,
                product_name TEXT DEFAULT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS naming_convention (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lineage (
                id TEXT PRIMARY KEY,
                source_ids TEXT NOT NULL,
                output_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                operation_detail TEXT,
                created_at TEXT NOT NULL
            )
        """)
        # 기존 DB 마이그레이션
        for col, definition in [
            ("pkl_key", "TEXT DEFAULT NULL"),
            ("standardized_name", "TEXT DEFAULT NULL"),
            ("product_name", "TEXT DEFAULT NULL"),
        ]:
            try:
                conn.execute(f"ALTER TABLE files ADD COLUMN {col} {definition}")
            except Exception:
                pass


def save_file_metadata(meta: dict):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO files
                (id, original_filename, stored_path, file_format, category, description,
                 tags, columns_info, row_count, col_count, upload_date, project_name,
                 file_size, pkl_key, standardized_name, product_name)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                meta["id"],
                meta["original_filename"],
                meta["stored_path"],
                meta["file_format"],
                meta.get("category", ""),
                meta.get("description", ""),
                json.dumps(meta.get("tags", []), ensure_ascii=False),
                json.dumps(meta.get("columns_info", []), ensure_ascii=False),
                meta.get("row_count", 0),
                meta.get("col_count", 0),
                meta["upload_date"],
                meta.get("project_name", ""),
                meta.get("file_size", 0),
                meta.get("pkl_key"),
                meta.get("standardized_name"),
                meta.get("product_name"),
            ),
        )


def update_file_metadata(file_id: str, updates: dict):
    with get_db() as conn:
        fields, values = [], []
        for k, v in updates.items():
            if k in ("tags", "columns_info"):
                v = json.dumps(v, ensure_ascii=False)
            fields.append(f"{k} = ?")
            values.append(v)
        values.append(file_id)
        conn.execute(f"UPDATE files SET {', '.join(fields)} WHERE id = ?", values)


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d["tags"])
    d["columns_info"] = json.loads(d["columns_info"])
    return d


def get_all_files(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    project: Optional[str] = None,
) -> List[dict]:
    with get_db() as conn:
        query = "SELECT * FROM files WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if project:
            query += " AND project_name = ?"
            params.append(project)
        rows = conn.execute(query, params).fetchall()
    result = []
    for row in rows:
        d = _row_to_dict(row)
        if tag and tag not in d["tags"]:
            continue
        result.append(d)
    return result


def get_file_by_id(file_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def delete_file_record(file_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))


def get_distinct_categories() -> List[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM files WHERE category != '' ORDER BY category"
        ).fetchall()
    return [r[0] for r in rows]


def get_distinct_projects() -> List[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT project_name FROM files WHERE project_name != '' ORDER BY project_name"
        ).fetchall()
    return [r[0] for r in rows]


def get_all_tags() -> List[str]:
    with get_db() as conn:
        rows = conn.execute("SELECT tags FROM files").fetchall()
    all_tags: set = set()
    for row in rows:
        all_tags.update(json.loads(row[0]))
    return sorted(all_tags)


# ── naming_convention CRUD ─────────────────────────────────────────────────────

def get_conventions() -> dict:
    """field별로 그룹핑된 컨벤션 목록 반환."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, field, value, description FROM naming_convention ORDER BY field, id"
        ).fetchall()
    result: dict = {"domain": [], "data_type": [], "stage": []}
    for row in rows:
        d = dict(row)
        field = d.pop("field")
        if field in result:
            result[field].append(d)
    return result


def add_convention(field: str, value: str, description: str, created_at: str) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO naming_convention (field, value, description, created_at) VALUES (?,?,?,?)",
            (field, value, description, created_at),
        )
        return cursor.lastrowid


def delete_convention(convention_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM naming_convention WHERE id = ?", (convention_id,))


def get_conventions_flat() -> List[dict]:
    """API 응답용 — 컨벤션 전체를 flat 리스트로 반환."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, field, value, description, created_at FROM naming_convention ORDER BY field, id"
        ).fetchall()
    return [dict(row) for row in rows]


def save_lineage(record: dict):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO lineage (id, source_ids, output_id, operation, operation_detail, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (
                record["id"],
                record["source_ids"],
                record["output_id"],
                record["operation"],
                record.get("operation_detail"),
                record["created_at"],
            ),
        )


def get_all_lineage() -> List[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM lineage ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_all_standardized_names() -> List[str]:
    """LLM 프롬프트 컨텍스트용 — 기존 standardized_name 목록."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT standardized_name FROM files WHERE standardized_name IS NOT NULL"
        ).fetchall()
    return [r[0] for r in rows]
