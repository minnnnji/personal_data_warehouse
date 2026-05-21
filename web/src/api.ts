import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export interface FileMetadata {
  id: string
  original_filename: string
  standardized_name: string | null
  product_name: string | null
  stored_path: string
  category: string | null
  project_name: string | null
  description: string | null
  tags: string[]
  columns_info: { name: string; dtype: string; null_count: number; sample_values: string[] }[]
  row_count: number
  col_count: number
  file_format: string | null
  upload_date: string
  pkl_key: string | null
}

export interface UploadAnalysisResult {
  file_id: string
  original_filename: string
  file_format: string
  row_count: number
  col_count: number
  columns_info: FileMetadata['columns_info']
  standardized_name: string | null
  product_name: string | null
  category: string | null
  project_name: string | null
  description: string | null
  tags: string[]
  uncertain: boolean
  question_for_user: string | null
  pkl_count: number | null
}

export interface Convention {
  id: number
  field: string
  value: string
  description: string | null
  created_at: string
}

export interface LineageNode {
  id: string
  label: string
  color: string
  title: string
}

export interface LineageEdge {
  from: string
  to: string
  label: string
}

export interface LineageData {
  nodes: LineageNode[]
  edges: LineageEdge[]
}

// 파일 목록
export const getFiles = (params?: { category?: string; project?: string; tag?: string }) =>
  api.get<FileMetadata[]>('/files', { params }).then(r => r.data)

// 파일 미리보기 - backend returns {columns, data, total_rows, preview_rows}
export const previewFile = (id: string) =>
  api.get<{ columns: string[]; data: Record<string, unknown>[]; total_rows: number }>(`/files/${id}/preview`)
    .then(r => ({ columns: r.data.columns, rows: r.data.data, row_count: r.data.total_rows }))

// 파일 삭제
export const deleteFile = (id: string) =>
  api.delete(`/files/${id}`).then(r => r.data)

// 파일 메타데이터 수정
export const patchFile = (id: string, data: Partial<FileMetadata>) =>
  api.patch(`/files/${id}`, data).then(r => r.data)

// 파일 업로드 - backend returns {file_id, metadata:{...}, uncertain, question_for_user, pkl_count}
export const uploadFile = (file: File): Promise<UploadAnalysisResult> => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => {
    const { file_id, metadata, uncertain, question_for_user, pkl_count } = r.data
    return {
      file_id,
      original_filename: metadata.original_filename,
      file_format: metadata.file_format,
      row_count: metadata.row_count,
      col_count: metadata.col_count,
      columns_info: metadata.columns_info,
      standardized_name: metadata.standardized_name,
      product_name: metadata.product_name,
      category: metadata.category,
      project_name: metadata.project_name,
      description: metadata.description,
      tags: metadata.tags,
      uncertain,
      question_for_user,
      pkl_count,
    }
  })
}

// 업로드 확정
export const confirmUpload = (data: {
  file_id: string
  standardized_name: string
  product_name: string
  category: string
  project_name: string
  description: string
  tags: string[]
  user_answer?: string
}) => api.post('/upload/confirm', data).then(r => r.data)

// 자연어 검색 - backend returns {answer, mentioned_file_ids, all_files}
export const queryFiles = (query: string) =>
  api.post('/query', { query }).then(r => ({
    answer: r.data.answer as string,
    file_ids: (r.data.mentioned_file_ids ?? []) as string[],
  }))

// 자연어 결합 - backend returns {generated_code, result_id, preview:{columns,data}, row_count, col_count}
export const combineGenerate = (file_ids: string[], command: string) =>
  api.post('/combine', { file_ids, command }).then(r => ({
    code: r.data.generated_code as string,
    preview: (r.data.preview?.data ?? []) as Record<string, unknown>[],
    previewColumns: (r.data.preview?.columns ?? []) as string[],
    row_count: r.data.row_count as number,
    col_count: r.data.col_count as number,
    result_id: r.data.result_id as string,
  }))

// 결합 결과 저장
export const combineSave = (data: {
  result_id: string
  file_ids: string[]
  standardized_name: string
  description: string
  category: string
  project_name: string
  tags: string[]
  code: string
}) => api.post<FileMetadata>('/combine/save', data).then(r => r.data)

// 네이밍 컨벤션 목록 (flat)
export const getConventions = () =>
  api.get<Convention[]>('/convention').then(r => r.data)

// 컨벤션 추가
export const addConvention = (data: { field: string; value: string; description?: string }) =>
  api.post<Convention>('/convention', data).then(r => r.data)

// 컨벤션 삭제
export const deleteConvention = (id: number) =>
  api.delete(`/convention/${id}`).then(r => r.data)

// Lineage 데이터
export const getLineage = () =>
  api.get<LineageData>('/lineage').then(r => r.data)

// 다운로드 URL
export const downloadUrl = (id: string, format: string) =>
  `/api/files/${id}/download?format=${format}`
