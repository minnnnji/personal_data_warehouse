import { Database, Upload, Search, GitMerge, GitBranch, Settings } from 'lucide-react'

export type Page = 'warehouse' | 'upload' | 'search' | 'combine' | 'lineage' | 'convention'

interface SidebarProps {
  page: Page
  onPageChange: (p: Page) => void
  // 필터 (창고 탭에서만 사용)
  categories: string[]
  projects: string[]
  tags: string[]
  selCat: string
  selProj: string
  selTag: string
  onCatChange: (v: string) => void
  onProjChange: (v: string) => void
  onTagChange: (v: string) => void
}

const NAV: { key: Page; label: string; icon: React.ReactNode }[] = [
  { key: 'warehouse', label: '파일 창고', icon: <Database size={15} /> },
  { key: 'upload', label: '업로드', icon: <Upload size={15} /> },
  { key: 'search', label: '검색', icon: <Search size={15} /> },
  { key: 'combine', label: '결합', icon: <GitMerge size={15} /> },
  { key: 'lineage', label: 'Lineage', icon: <GitBranch size={15} /> },
]

export default function Sidebar(props: SidebarProps) {
  const { page, onPageChange, categories, projects, tags, selCat, selProj, selTag, onCatChange, onProjChange, onTagChange } = props
  const showFilters = page === 'warehouse'

  return (
    <aside style={{
      width: 220, flexShrink: 0, height: '100vh', position: 'sticky', top: 0,
      background: 'var(--surface)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', overflowY: 'auto',
    }}>
      {/* 로고 */}
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: 26, height: 26, borderRadius: '7px', background: 'var(--action-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Database size={13} color="white" />
          </div>
          <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--ink)', letterSpacing: '-0.3px' }}>
            Data Warehouse
          </span>
        </div>
      </div>

      {/* 메인 네비게이션 */}
      <nav style={{ padding: '8px 8px', flex: 1 }}>
        <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-tertiary)', letterSpacing: '0.5px', textTransform: 'uppercase', padding: '6px 8px 4px' }}>메뉴</p>
        {NAV.map(n => (
          <button
            key={n.key}
            onClick={() => onPageChange(n.key)}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px', width: '100%',
              padding: '7px 10px', borderRadius: '8px', fontSize: '13.5px',
              fontWeight: page === n.key ? 600 : 400,
              color: page === n.key ? 'var(--action-blue)' : 'var(--ink-secondary)',
              background: page === n.key ? 'rgba(0,102,204,0.08)' : 'transparent',
              border: 'none', cursor: 'pointer', textAlign: 'left',
              transition: 'all 0.1s', letterSpacing: '-0.1px',
              fontFamily: 'inherit',
            }}
            onMouseEnter={e => { if (page !== n.key) e.currentTarget.style.background = 'var(--parchment)' }}
            onMouseLeave={e => { if (page !== n.key) e.currentTarget.style.background = 'transparent' }}
          >
            {n.icon}
            {n.label}
          </button>
        ))}

        {/* 카테고리 필터 (창고 탭에서만) */}
        {showFilters && (categories.length > 0 || projects.length > 0 || tags.length > 0) && (
          <div style={{ marginTop: '16px' }}>
            <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-tertiary)', letterSpacing: '0.5px', textTransform: 'uppercase', padding: '0 8px 6px' }}>필터</p>

            {categories.length > 0 && (
              <div style={{ marginBottom: '12px', padding: '0 4px' }}>
                <p style={{ fontSize: '11px', fontWeight: 500, color: 'var(--ink-tertiary)', padding: '0 6px 4px' }}>카테고리</p>
                {categories.map(c => (
                  <label key={c} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 6px', borderRadius: '6px', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="cat"
                      checked={selCat === c}
                      onChange={() => onCatChange(selCat === c ? '' : c)}
                      style={{ accentColor: 'var(--action-blue)', cursor: 'pointer' }}
                    />
                    <span style={{ fontSize: '13px', color: 'var(--ink)', letterSpacing: '-0.1px' }}>{c}</span>
                  </label>
                ))}
                {selCat && (
                  <button onClick={() => onCatChange('')} style={{ fontSize: '11px', color: 'var(--action-blue)', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px' }}>
                    초기화
                  </button>
                )}
              </div>
            )}

            {projects.length > 0 && (
              <div style={{ marginBottom: '12px', padding: '0 4px' }}>
                <p style={{ fontSize: '11px', fontWeight: 500, color: 'var(--ink-tertiary)', padding: '0 6px 4px' }}>프로젝트</p>
                {projects.map(p => (
                  <label key={p} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 6px', borderRadius: '6px', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="proj"
                      checked={selProj === p}
                      onChange={() => onProjChange(selProj === p ? '' : p)}
                      style={{ accentColor: 'var(--action-blue)', cursor: 'pointer' }}
                    />
                    <span style={{ fontSize: '13px', color: 'var(--ink)', letterSpacing: '-0.1px' }}>{p}</span>
                  </label>
                ))}
                {selProj && (
                  <button onClick={() => onProjChange('')} style={{ fontSize: '11px', color: 'var(--action-blue)', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px' }}>
                    초기화
                  </button>
                )}
              </div>
            )}

            {tags.length > 0 && (
              <div style={{ padding: '0 4px' }}>
                <p style={{ fontSize: '11px', fontWeight: 500, color: 'var(--ink-tertiary)', padding: '0 6px 4px' }}>태그</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', padding: '0 6px' }}>
                  {tags.slice(0, 12).map(t => (
                    <button
                      key={t}
                      onClick={() => onTagChange(selTag === t ? '' : t)}
                      style={{
                        padding: '2px 8px', borderRadius: '9999px', fontSize: '11px',
                        border: `1px solid ${selTag === t ? 'var(--action-blue)' : 'var(--border)'}`,
                        background: selTag === t ? 'rgba(0,102,204,0.08)' : 'transparent',
                        color: selTag === t ? 'var(--action-blue)' : 'var(--ink-secondary)',
                        cursor: 'pointer', fontFamily: 'inherit',
                      }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </nav>

      {/* 하단: 컨벤션 설정 */}
      <div style={{ padding: '8px', borderTop: '1px solid var(--border)' }}>
        <button
          onClick={() => onPageChange('convention')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px', width: '100%',
            padding: '7px 10px', borderRadius: '8px', fontSize: '13px',
            fontWeight: page === 'convention' ? 600 : 400,
            color: page === 'convention' ? 'var(--action-blue)' : 'var(--ink-tertiary)',
            background: page === 'convention' ? 'rgba(0,102,204,0.08)' : 'transparent',
            border: 'none', cursor: 'pointer', textAlign: 'left',
            transition: 'all 0.1s', fontFamily: 'inherit',
          }}
          onMouseEnter={e => { if (page !== 'convention') e.currentTarget.style.background = 'var(--parchment)' }}
          onMouseLeave={e => { if (page !== 'convention') e.currentTarget.style.background = 'transparent' }}
        >
          <Settings size={14} />
          컨벤션 설정
        </button>
      </div>
    </aside>
  )
}
