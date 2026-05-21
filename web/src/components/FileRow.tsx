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

const CAT_COLOR: Record<string, { bg: string; text: string }> = {
  PR:   { bg: '#f3e8ff', text: '#6d28d9' },
  WFR:  { bg: '#d1fae5', text: '#065f46' },
  IQC:  { bg: '#fef3c7', text: '#92400e' },
  CDA:  { bg: '#dbeafe', text: '#1e40af' },
  생산: { bg: '#d1fae5', text: '#065f46' },
  품질: { bg: '#dbeafe', text: '#1e40af' },
  영업: { bg: '#fef3c7', text: '#92400e' },
  물류: { bg: '#ede9fe', text: '#5b21b6' },
  인사: { bg: '#fce7f3', text: '#9d174d' },
  재무: { bg: '#d1fae5', text: '#065f46' },
  설비: { bg: '#f1f5f9', text: '#475569' },
  기타: { bg: '#f4f4f5', text: '#52525b' },
}

function CategoryDot({ cat }: { cat: string | null }) {
  const c = CAT_COLOR[cat ?? ''] ?? { bg: '#f4f4f5', text: '#52525b' }
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      background: c.text, flexShrink: 0, marginTop: 2,
    }} />
  )
}

export default function FileRow({ file, selected, onSelect, onDelete, showCheckbox }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [preview, setPreview] = useState<{ columns: string[]; rows: Record<string, unknown>[] } | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [hovering, setHovering] = useState(false)
  const [downloadOpen, setDownloadOpen] = useState(false)

  const displayName = file.standardized_name || file.original_filename
  const catColor = CAT_COLOR[file.category ?? ''] ?? { bg: '#f4f4f5', text: '#52525b' }

  const togglePreview = async () => {
    if (expanded) { setExpanded(false); return }
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

  return (
    <div
      className="fade-in"
      style={{ borderBottom: '1px solid var(--border)' }}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
    >
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        padding: '9px 16px', minHeight: '44px',
        background: hovering ? 'var(--parchment)' : 'transparent',
        transition: 'background 0.1s',
      }}>
        {showCheckbox && (
          <input
            type="checkbox"
            checked={selected}
            onChange={e => onSelect?.(file.id, e.target.checked)}
            style={{ cursor: 'pointer', accentColor: 'var(--action-blue)', width: 14, height: 14, flexShrink: 0 }}
          />
        )}

        {/* 컬러 닷 */}
        <CategoryDot cat={file.category} />

        {/* 파일명 + 뱃지 */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
          <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--ink)', letterSpacing: '-0.2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {displayName}
          </span>
          {file.file_format && (
            <span style={{ fontSize: '11px', padding: '1px 6px', borderRadius: '4px', background: 'var(--parchment)', color: 'var(--ink-secondary)', fontWeight: 500, textTransform: 'uppercase', flexShrink: 0 }}>
              {file.file_format}
            </span>
          )}
          {file.category && (
            <span style={{ fontSize: '11px', padding: '1px 6px', borderRadius: '4px', background: catColor.bg, color: catColor.text, fontWeight: 500, flexShrink: 0 }}>
              {file.category}
            </span>
          )}
        </div>

        {/* 메타 정보 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: 'var(--ink-tertiary)', flexShrink: 0 }}>
          <span>{file.row_count.toLocaleString()}행</span>
          <span>{file.col_count}열</span>
          {file.project_name && (
            <span style={{ maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.project_name}</span>
          )}
        </div>

        {/* 태그 */}
        <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
          {file.tags.slice(0, 3).map(t => (
            <span key={t} style={{ fontSize: '11px', padding: '1px 6px', borderRadius: '4px', background: 'rgba(0,102,204,0.07)', color: 'var(--action-blue)' }}>
              {t}
            </span>
          ))}
        </div>

        {/* 액션 버튼 (hover 시 표시) */}
        <div style={{ display: 'flex', gap: '4px', opacity: hovering ? 1 : 0, transition: 'opacity 0.1s', flexShrink: 0 }}>
          <button
            className="btn-secondary"
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={togglePreview}
          >
            {loadingPreview
              ? <span className="spinner" style={{ width: 12, height: 12 }} />
              : expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            미리보기
          </button>

          <div style={{ position: 'relative' }}>
            <button
              className="btn-secondary"
              style={{ padding: '4px 10px', fontSize: '12px' }}
              onClick={() => setDownloadOpen(v => !v)}
              onBlur={() => setTimeout(() => setDownloadOpen(false), 150)}
            >
              <Download size={12} />
            </button>
            {downloadOpen && (
              <div style={{
                position: 'absolute', right: 0, top: '100%', marginTop: '4px',
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: '10px', padding: '4px', zIndex: 100, minWidth: '110px',
                boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
              }}>
                {['csv', 'xlsx', 'pkl', 'parquet'].map(fmt => (
                  <a
                    key={fmt}
                    href={downloadUrl(file.id, fmt)}
                    download
                    style={{ display: 'block', padding: '6px 12px', fontSize: '13px', color: 'var(--ink)', textDecoration: 'none', borderRadius: '6px' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--parchment)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    {fmt.toUpperCase()}
                  </a>
                ))}
              </div>
            )}
          </div>

          {onDelete && (
            <button
              className="btn-danger"
              style={{ padding: '4px 8px', fontSize: '12px' }}
              onClick={() => onDelete(file.id)}
            >
              <Trash2 size={12} />
            </button>
          )}
        </div>
      </div>

      {/* 미리보기 테이블 */}
      {expanded && preview && (
        <div style={{ overflowX: 'auto', background: 'var(--parchment)', borderTop: '1px solid var(--border)' }}>
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {preview.columns.map(col => (
                  <th key={col} style={{ padding: '6px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--ink-secondary)', whiteSpace: 'nowrap', borderBottom: '1px solid var(--border)', background: 'var(--parchment)' }}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row, i) => (
                <tr key={i} style={{ background: i % 2 === 0 ? 'var(--surface)' : 'var(--parchment)' }}>
                  {preview.columns.map(col => (
                    <td key={col} style={{ padding: '5px 12px', color: 'var(--ink)', whiteSpace: 'nowrap', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
