import { useState } from 'react'
import { ChevronDown, ChevronUp, Download, Trash2 } from 'lucide-react'
import { type FileMetadata, previewFile, downloadUrl } from '../api'

interface Props {
  file: FileMetadata
  selected?: boolean
  onSelect?: (id: string, checked: boolean) => void
  onDelete?: (id: string) => void
  showCheckbox?: boolean
}

export default function FileCard({ file, selected, onSelect, onDelete, showCheckbox }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [preview, setPreview] = useState<{ columns: string[]; rows: Record<string, unknown>[] } | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)

  const displayName = file.standardized_name || file.original_filename

  const togglePreview = async () => {
    if (expanded) {
      setExpanded(false)
      return
    }
    if (!preview) {
      setLoadingPreview(true)
      try {
        const data = await previewFile(file.id)
        setPreview(data)
      } finally {
        setLoadingPreview(false)
      }
    }
    setExpanded(true)
  }

  const categoryColor = (cat: string | null) => {
    const map: Record<string, string> = {
      생산: '#34c759', 품질: '#0066cc', 영업: '#ff9500',
      물류: '#5856d6', 인사: '#ff2d55', 재무: '#30d158',
      설비: '#636366', 기타: '#8e8e93',
    }
    return map[cat ?? ''] ?? '#8e8e93'
  }

  return (
    <div className="card fade-in" style={{ padding: '0' }}>
      <div style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          {showCheckbox && (
            <input
              type="checkbox"
              checked={selected}
              onChange={e => onSelect?.(file.id, e.target.checked)}
              style={{ marginTop: '3px', cursor: 'pointer', accentColor: 'var(--action-blue)', width: '16px', height: '16px', flexShrink: 0 }}
            />
          )}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* 헤더 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '6px' }}>
              {file.category && (
                <span
                  style={{
                    display: 'inline-flex', alignItems: 'center', padding: '2px 8px',
                    borderRadius: '9999px', fontSize: '11px', fontWeight: 600,
                    background: `${categoryColor(file.category)}18`,
                    color: categoryColor(file.category),
                    letterSpacing: '0.2px',
                  }}
                >
                  {file.category}
                </span>
              )}
              {file.pkl_key && (
                <span className="tag-gray" style={{ fontSize: '11px' }}>pkl</span>
              )}
              {file.file_format && (
                <span className="tag-gray" style={{ fontSize: '11px', textTransform: 'uppercase' }}>{file.file_format}</span>
              )}
            </div>

            <h3 style={{ margin: '0 0 4px', fontSize: '15px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px', wordBreak: 'break-all' }}>
              {displayName}
            </h3>

            {file.original_filename !== displayName && (
              <p style={{ margin: '0 0 4px', fontSize: '12px', color: 'var(--ink-tertiary)' }}>{file.original_filename}</p>
            )}

            {file.description && (
              <p style={{ margin: '0 0 8px', fontSize: '13px', color: 'var(--ink-secondary)', lineHeight: '1.5' }}>
                {file.description}
              </p>
            )}

            {/* 통계 */}
            <div style={{ display: 'flex', gap: '16px', marginBottom: '8px', fontSize: '12px', color: 'var(--ink-tertiary)' }}>
              <span>{file.row_count.toLocaleString()} 행</span>
              <span>{file.col_count} 열</span>
              {file.project_name && <span>📁 {file.project_name}</span>}
            </div>

            {/* 태그 */}
            {file.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {file.tags.map(t => <span key={t} className="tag">{t}</span>)}
              </div>
            )}
          </div>

          {/* 액션 버튼 */}
          <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
            <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '13px' }} onClick={togglePreview}>
              {loadingPreview ? <span className="spinner" style={{ width: 14, height: 14 }} /> : expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              미리보기
            </button>
            <div style={{ position: 'relative' }}>
              <DownloadMenu fileId={file.id} />
            </div>
            {onDelete && (
              <button className="btn-danger" style={{ padding: '6px 10px' }} onClick={() => onDelete(file.id)}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 미리보기 테이블 */}
      {expanded && preview && (
        <div style={{ borderTop: '1px solid var(--border)', overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--parchment)' }}>
                {preview.columns.map(col => (
                  <th key={col} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--ink-secondary)', whiteSpace: 'nowrap', borderBottom: '1px solid var(--border)' }}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--parchment)' }}>
                  {preview.columns.map(col => (
                    <td key={col} style={{ padding: '7px 12px', color: 'var(--ink)', whiteSpace: 'nowrap', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {String(row[col] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function DownloadMenu({ fileId }: { fileId: string }) {
  const [open, setOpen] = useState(false)
  const formats = ['csv', 'xlsx', 'pkl', 'parquet']

  return (
    <div style={{ position: 'relative' }}>
      <button
        className="btn-secondary"
        style={{ padding: '6px 12px', fontSize: '13px' }}
        onClick={() => setOpen(v => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      >
        <Download size={14} />
        다운로드
      </button>
      {open && (
        <div style={{
          position: 'absolute', right: 0, top: '100%', marginTop: '6px',
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px',
          padding: '6px', zIndex: 100, minWidth: '130px',
          boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
        }}>
          {formats.map(fmt => (
            <a
              key={fmt}
              href={downloadUrl(fileId, fmt)}
              download
              style={{
                display: 'block', padding: '8px 14px', fontSize: '13px',
                color: 'var(--ink)', textDecoration: 'none', borderRadius: '8px',
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--parchment)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              {fmt.toUpperCase()}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
