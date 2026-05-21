import { useState, useEffect } from 'react'
import { Search as SearchIcon } from 'lucide-react'
import { queryFiles, getFiles, type FileMetadata } from '../api'
import FileRow from '../components/FileRow'
import { toast } from '../components/Toast'

interface Props {
  initialQuery?: string
}

export default function Search({ initialQuery = '' }: Props) {
  const [query, setQuery] = useState(initialQuery)
  const [loading, setLoading] = useState(false)

  useEffect(() => { if (initialQuery) setQuery(initialQuery) }, [initialQuery])
  const [answer, setAnswer] = useState<string | null>(null)
  const [relatedFiles, setRelatedFiles] = useState<FileMetadata[]>([])

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setAnswer(null)
    setRelatedFiles([])
    try {
      const result = await queryFiles(query)
      setAnswer(result.answer)

      if (result.file_ids?.length) {
        const allFiles = await getFiles()
        setRelatedFiles(allFiles.filter(f => result.file_ids.includes(f.id)))
      }
    } catch {
      toast.error('검색 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px' }}>
          데이터 검색
        </h1>
        <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-tertiary)' }}>
          자연어로 원하는 데이터를 검색하세요.
        </p>
      </div>

      {/* 검색창 */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '28px' }}>
        <input
          className="input"
          style={{ flex: 1, fontSize: '15px' }}
          placeholder="예: lot_id가 있는 IQC 데이터를 찾아줘"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn-primary" onClick={handleSearch} disabled={loading || !query.trim()} style={{ padding: '10px 24px' }}>
          {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <SearchIcon size={14} />}
          검색
        </button>
      </div>

      {/* 결과 */}
      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <span className="spinner" style={{ width: 28, height: 28 }} />
        </div>
      )}

      {answer && !loading && (
        <div className="fade-in">
          {/* AI 답변 */}
          <div className="card" style={{ marginBottom: '20px', background: 'linear-gradient(135deg, #f0f7ff, #ffffff)' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--action-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <span style={{ fontSize: '14px', color: 'white', fontWeight: 700 }}>AI</span>
              </div>
              <div style={{ flex: 1 }}>
                <p style={{ margin: '0 0 4px', fontSize: '12px', color: 'var(--action-blue)', fontWeight: 600, letterSpacing: '0.2px' }}>AI 검색 결과</p>
                <div style={{ fontSize: '14px', color: 'var(--ink)', lineHeight: '1.65', whiteSpace: 'pre-wrap' }}>
                  {answer}
                </div>
              </div>
            </div>
          </div>

          {/* 관련 파일 */}
          {relatedFiles.length > 0 && (
            <div>
              <p style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--ink-tertiary)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                관련 파일 {relatedFiles.length}개
              </p>
              <div style={{ background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)', overflow: 'hidden' }}>
                {relatedFiles.map(file => <FileRow key={file.id} file={file} />)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 힌트 */}
      {!answer && !loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
          {[
            'lot_id가 있는 IQC 데이터 찾아줘',
            '2025년도 생산 데이터 목록',
            'A제품 관련 파일 모두 보여줘',
            '날짜 범위가 있는 품질 데이터',
          ].map(hint => (
            <button
              key={hint}
              onClick={() => { setQuery(hint); }}
              style={{
                padding: '12px 16px', borderRadius: '12px', fontSize: '13px',
                color: 'var(--ink-secondary)', background: 'var(--surface)',
                border: '1px solid var(--border)', cursor: 'pointer', textAlign: 'left',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--action-blue)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
            >
              &ldquo;{hint}&rdquo;
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
