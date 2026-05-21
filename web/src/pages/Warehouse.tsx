import { useState } from 'react'
import { Trash2, Database, RefreshCw } from 'lucide-react'
import { deleteFile, type FileMetadata } from '../api'
import FileRow from '../components/FileRow'
import { toast } from '../components/Toast'

interface Props {
  files: FileMetadata[]
  onRefresh: () => void
  onFileDeleted: (id: string) => void
}

export default function Warehouse({ files, onRefresh, onFileDeleted }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)

  const onSelect = (id: string, checked: boolean) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const onSelectAll = (checked: boolean) => {
    setSelected(checked ? new Set(files.map(f => f.id)) : new Set())
  }

  const handleDelete = async (id: string) => {
    if (!confirm('이 파일을 삭제하시겠습니까?')) return
    try {
      await deleteFile(id)
      onFileDeleted(id)
      setSelected(prev => { const next = new Set(prev); next.delete(id); return next })
      toast.success('삭제되었습니다.')
    } catch {
      toast.error('삭제에 실패했습니다.')
    }
  }

  const handleBulkDelete = async () => {
    if (!selected.size) return
    if (!confirm(`선택한 ${selected.size}개 파일을 삭제하시겠습니까?`)) return
    setDeleting(true)
    try {
      await Promise.all([...selected].map(id => deleteFile(id)))
      selected.forEach(id => onFileDeleted(id))
      setSelected(new Set())
      toast.success(`${selected.size}개 파일이 삭제되었습니다.`)
    } catch {
      toast.error('일부 삭제에 실패했습니다.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px' }}>
            파일 창고
          </h1>
          <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-tertiary)' }}>
            {files.length}개 파일
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {selected.size > 0 && (
            <button className="btn-danger" style={{ padding: '6px 14px', fontSize: '13px' }} onClick={handleBulkDelete} disabled={deleting}>
              <Trash2 size={13} />
              {selected.size}개 삭제
            </button>
          )}
          <button className="btn-secondary" style={{ padding: '6px 14px', fontSize: '13px' }} onClick={onRefresh}>
            <RefreshCw size={13} />
            새로고침
          </button>
        </div>
      </div>

      {/* 파일 리스트 */}
      {files.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '80px 0', background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <Database size={36} style={{ color: 'var(--ink-tertiary)', margin: '0 auto 12px' }} />
          <p style={{ color: 'var(--ink-tertiary)', fontSize: '14px', margin: '0 0 4px' }}>저장된 파일이 없습니다.</p>
          <p style={{ color: 'var(--ink-tertiary)', fontSize: '12px', margin: 0 }}>파일을 업로드해 창고를 채워보세요.</p>
        </div>
      ) : (
        <div style={{ background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)', overflow: 'hidden' }}>
          {/* 테이블 헤더 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 16px', background: 'var(--parchment)', borderBottom: '1px solid var(--border)' }}>
            <input
              type="checkbox"
              checked={selected.size === files.length && files.length > 0}
              onChange={e => onSelectAll(e.target.checked)}
              style={{ cursor: 'pointer', accentColor: 'var(--action-blue)', width: 14, height: 14, flexShrink: 0 }}
            />
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-tertiary)', letterSpacing: '0.3px', textTransform: 'uppercase' }}>
              파일명
            </span>
            <div style={{ flex: 1 }} />
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-tertiary)', letterSpacing: '0.3px', textTransform: 'uppercase' }}>
              크기
            </span>
            <div style={{ width: 80 }} />
          </div>

          {files.map(file => (
            <FileRow
              key={file.id}
              file={file}
              selected={selected.has(file.id)}
              onSelect={onSelect}
              onDelete={handleDelete}
              showCheckbox
            />
          ))}
        </div>
      )}
    </div>
  )
}
