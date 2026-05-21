import { useState, useEffect, useCallback } from 'react'
import { Upload, Search } from 'lucide-react'
import Sidebar, { type Page } from './components/Sidebar'
import { ToastContainer } from './components/Toast'
import { getFiles, type FileMetadata } from './api'
import Warehouse from './pages/Warehouse'
import UploadPage from './pages/Upload'
import SearchPage from './pages/Search'
import CombinePage from './pages/Combine'
import LineagePage from './pages/Lineage'
import ConventionPage from './pages/Convention'

export default function App() {
  const [page, setPage] = useState<Page>('warehouse')
  const [files, setFiles] = useState<FileMetadata[]>([])
  const [selCat, setSelCat] = useState('')
  const [selProj, setSelProj] = useState('')
  const [selTag, setSelTag] = useState('')
  const [headerSearch, setHeaderSearch] = useState('')

  const loadFiles = useCallback(async () => {
    try {
      const data = await getFiles({ category: selCat || undefined, project: selProj || undefined, tag: selTag || undefined })
      setFiles(data)
    } catch { /* 무시 */ }
  }, [selCat, selProj, selTag])

  useEffect(() => { loadFiles() }, [loadFiles])

  // 사이드바 필터용
  const allFiles = files  // 필터된 목록
  const categories = [...new Set(files.map(f => f.category).filter(Boolean))] as string[]
  const projects = [...new Set(files.map(f => f.project_name).filter(Boolean))] as string[]
  const tags = [...new Set(files.flatMap(f => f.tags))]

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--parchment)' }}>
      {/* 좌측 사이드바 */}
      <Sidebar
        page={page}
        onPageChange={setPage}
        categories={categories}
        projects={projects}
        tags={tags}
        selCat={selCat}
        selProj={selProj}
        selTag={selTag}
        onCatChange={setSelCat}
        onProjChange={setSelProj}
        onTagChange={setSelTag}
      />

      {/* 우측 전체 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* 상단 헤더 (48px) */}
        <header style={{
          height: 48, display: 'flex', alignItems: 'center', gap: '12px',
          padding: '0 20px', background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
          position: 'sticky', top: 0, zIndex: 50,
        }}>
          {/* 검색창 */}
          <div style={{ flex: 1, position: 'relative', maxWidth: '400px' }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--ink-tertiary)' }} />
            <input
              className="input"
              style={{ paddingLeft: 30, height: 32, fontSize: '13px' }}
              placeholder="검색... (⌘K)"
              value={headerSearch}
              onChange={e => setHeaderSearch(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && headerSearch.trim()) {
                  setPage('search')
                }
              }}
            />
          </div>

          <div style={{ flex: 1 }} />

          {/* 업로드 버튼 */}
          <button className="btn-primary" style={{ padding: '6px 16px', fontSize: '13px' }} onClick={() => setPage('upload')}>
            <Upload size={13} />
            업로드
          </button>
        </header>

        {/* 메인 콘텐츠 */}
        <main style={{ flex: 1, padding: '24px 28px', overflowY: 'auto' }}>
          {page === 'warehouse' && (
            <Warehouse
              files={allFiles}
              onRefresh={loadFiles}
              onFileDeleted={(id) => setFiles(prev => prev.filter(f => f.id !== id))}
            />
          )}
          {page === 'upload' && <UploadPage onUploaded={loadFiles} />}
          {page === 'search' && <SearchPage initialQuery={headerSearch} />}
          {page === 'combine' && <CombinePage />}
          {page === 'lineage' && <LineagePage />}
          {page === 'convention' && <ConventionPage />}
        </main>
      </div>

      <ToastContainer />
    </div>
  )
}
