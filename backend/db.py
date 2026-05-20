import sqlite3
import json
from typing import List, Optional
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "warehouse.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
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
            file_size INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_file_metadata(meta: dict):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO files
            (id, original_filename, stored_path, file_format, category, description,
             tags, columns_info, row_count, col_count, upload_date, project_name, file_size)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            meta["id"],
            meta["original_filename"],
            meta["stored_path"],
            meta["file_format"],
            meta["category"],
            meta["description"],
            json.dumps(meta["tags"], ensure_ascii=False),
            json.dumps(meta["columns_info"], ensure_ascii=False),
            meta["row_count"],
            meta["col_count"],
            meta["upload_date"],
            meta["project_name"],
            meta["file_size"],
        ),
    )
    conn.commit()
    conn.close()


def update_file_metadata(file_id: str, updates: dict):
    conn = get_conn()
    fields, values = [], []
    for k, v in updates.items():
        if k in ("tags", "columns_info"):
            v = json.dumps(v, ensure_ascii=False)
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(file_id)
    conn.execute(f"UPDATE files SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


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
    conn = get_conn()
    query = "SELECT * FROM files WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if project:
        query += " AND project_name = ?"
        params.append(project)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = _row_to_dict(row)
        if tag and tag not in d["tags"]:
            continue
        result.append(d)
    return result


def get_file_by_id(file_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_dict(row)


def delete_file_record(file_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()


def get_distinct_categories() -> List[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT category FROM files WHERE category != '' ORDER BY category"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_distinct_projects() -> List[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT project_name FROM files WHERE project_name != '' ORDER BY project_name"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_all_tags() -> List[str]:
    conn = get_conn()
    rows = conn.execute("SELECT tags FROM files").fetchall()
    conn.close()
    all_tags: set = set()
    for row in rows:
        all_tags.update(json.loads(row[0]))
    return sorted(all_tags)
