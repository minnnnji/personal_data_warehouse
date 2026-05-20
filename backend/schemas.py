from pydantic import BaseModel
from typing import Optional, List, Any, Dict


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    null_count: int
    sample_values: List[str]


class FileMetadata(BaseModel):
    id: str
    original_filename: str
    stored_path: str
    file_format: str
    category: str
    description: str
    tags: List[str]
    columns_info: List[Dict[str, Any]]
    row_count: int
    col_count: int
    upload_date: str
    project_name: str
    file_size: int


class UploadResponse(BaseModel):
    file_id: str
    metadata: FileMetadata
    uncertain: bool
    question_for_user: Optional[str] = None


class ConfirmUploadRequest(BaseModel):
    file_id: str
    category: str
    description: str
    tags: List[str]
    project_name: str
    user_answer: Optional[str] = None


class QueryRequest(BaseModel):
    query: str


class CombineRequest(BaseModel):
    file_ids: List[str]
    command: str
