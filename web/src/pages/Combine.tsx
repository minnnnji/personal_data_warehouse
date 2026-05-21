import { useState, useEffect } from 'react'
import { Code, Play, Save, ChevronDown, ChevronUp } from 'lucide-react'
import { getFiles, combineGenerate, combineSave, type FileMetadata } from '../api'
import { toast } from '../components/Toast'

export default function Combine() {
  const [files, setFiles] = useState<FileMetadata[]>([])
  const [loadingFiles, setLoadingFiles] = useState(true)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [command, setCommand] = useState('')
  const [generating, setGenerating] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [result, setResult] = useState<{
    code: string
    preview: Record<string, unknown>[]
    previewColumns: string[]
    row_count: number
    col_count: number
    result_id: string
  } | null>(null)
  const [codeExpanded, setCodeExpanded] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // 저장 폼
  const [saveForm, setSaveForm] = useState({
    standardized_name: '', description: '', category: '', project_name: '', tags: '',
  })

  useEffect(() => {
    getFiles().then(setFiles).finally(() => setLoadingFiles(false))
  }, [])

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectedFiles = files.filter(f => selectedIds.has(f.id))

  const handleGenerate = async () => {
    if (selectedIds.size < 1) { toast.error('파일을 1개 이상 선택하세요.'); return }
    if (!command.trim()) { toast.error('결합 명령을 입력하세요.'); return }
    setGenerating(true)
    setResult(null)
    setSaved(false)
    try {
      const r = await combineGenerate([...selectedIds], command)
      setResult(r)
      setCodeExpanded(true)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '코드 생성에 실패했습니다.'
      toast.error(msg)
    } finally {
      setGenerating(false)
    }
  }

  const handleExecute = async () => {
    if (!result) return
    setExecuting(true)
    try {
      const r = await combineGenerate([...selectedIds], command)
      setResult(r)
      setSaved(false)
      toast.success('재실행 완료!')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '실행에 실패했습니다.'
      toast.error(msg)
    } finally {
      setExecuting(false)
    }
  }

  const handleSave = async () => {
    if (!result) return
    setSaving(true)
    try {
      await combineSave({
        result_id: result.result_id,
        file_ids: [...selectedIds],
        standardized_name: saveForm.standardized_name,
        description: saveForm.description,
        category: saveForm.category,
        project_name: saveForm.project_name,
        tags: saveForm.tags.split(',').map(t => t.trim()).filter(Boolean),
        code: result.code,
      })
      toast.success('결합 결과가 창고에 저장되었습니다.')
      setSaved(true)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '저장에 실패했습니다.'
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px' }}>
          데이터 결합
        </h1>
        <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-tertiary)' }}>
          자연어 명령으로 파일을 병합하거나 변환합니다.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '20px', alignItems: 'start' }}>
        {/* 파일 선택 패널 */}
        <div className="card" style={{ position: 'sticky', top: '20px' }}>
          <h3 style={{ margin: '0 0 14px', fontSize: '14px', fontWeight: 600, color: 'var(--ink-secondary)', letterSpacing: '-0.2px' }}>
            파일 선택 ({selectedIds.size}개)
          </h3>
          {loadingFiles ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '24px' }}>
              <span className="spinner" />
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '400px', overflowY: 'auto' }}>
              {files.map(f => (
                <label
                  key={f.id}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '10px 12px', borderRadius: '10px',
                    cursor: 'pointer', transition: 'background 0.1s',
                    background: selectedIds.has(f.id) ? 'rgba(0,102,204,0.06)' : 'transparent',
                    border: `1px solid ${selectedIds.has(f.id) ? 'rgba(0,102,204,0.2)' : 'transparent'}`,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(f.id)}
                    onChange={() => toggleSelect(f.id)}
                    style={{ marginTop: '2px', accentColor: 'var(--action-blue)', cursor: 'pointer', flexShrink: 0 }}
                  />
                  <div style={{ minWidth: 0 }}>
                    <p style={{ margin: 0, fontSize: '13px', fontWeight: 500, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.standardized_name || f.original_filename}
                    </p>
                    <p style={{ margin: 0, fontSize: '11px', color: 'var(--ink-tertiary)' }}>
                      {f.row_count.toLocaleString()} 행 · {f.col_count} 열
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* 명령 + 결과 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* 선택된 파일 컬럼 요약 */}
          {selectedFiles.length > 0 && (
            <div className="card" style={{ background: 'var(--parchment)' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', fontWeight: 600, color: 'var(--ink-secondary)' }}>선택된 파일 컬럼</h3>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                {selectedFiles.map((f, i) => (
                  <div key={f.id}>
                    <p style={{ margin: '0 0 6px', fontSize: '12px', fontWeight: 600, color: 'var(--action-blue)' }}>
                      df_{i}: {f.standardized_name || f.original_filename}
                    </p>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {f.columns_info.slice(0, 8).map(c => (
                        <span key={c.name} className="tag-gray" style={{ fontSize: '11px' }}>{c.name}</span>
                      ))}
                      {f.columns_info.length > 8 && (
                        <span className="tag-gray" style={{ fontSize: '11px' }}>+{f.columns_info.length - 8}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 명령 입력 */}
          <div className="card">
            <label className="label">자연어 명령</label>
            <textarea
              className="input"
              style={{ height: '80px', resize: 'vertical', marginBottom: '14px' }}
              placeholder="예: lot_id 기준으로 df_0과 df_1을 left join해줘"
              value={command}
              onChange={e => setCommand(e.target.value)}
            />
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button className="btn-primary" onClick={handleGenerate} disabled={generating || selectedIds.size === 0}>
                {generating ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Code size={14} />}
                코드 생성
              </button>
            </div>
          </div>

          {/* 생성된 코드 */}
          {result && (
            <div className="card fade-in">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--ink)' }}>생성된 코드</h3>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => setCodeExpanded(v => !v)}>
                    {codeExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    {codeExpanded ? '접기' : '펼치기'}
                  </button>
                  <button className="btn-primary" style={{ padding: '6px 14px', fontSize: '12px' }} onClick={handleExecute} disabled={executing}>
                    {executing ? <span className="spinner" style={{ width: 12, height: 12 }} /> : <Play size={12} />}
                    실행
                  </button>
                </div>
              </div>
              {codeExpanded && (
                <pre style={{
                  margin: 0, padding: '16px', borderRadius: '10px',
                  background: '#1d1d1f', color: '#f5f5f7',
                  fontSize: '12px', lineHeight: '1.6', overflowX: 'auto',
                  fontFamily: 'ui-monospace, "SF Mono", Consolas, monospace',
                }}>
                  {result.code}
                </pre>
              )}
            </div>
          )}

          {/* 미리보기 결과 */}
          {result && result.preview.length > 0 && (
            <div className="card fade-in">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--ink)' }}>
                  결과 미리보기 ({result.row_count.toLocaleString()} 행 × {result.col_count} 열)
                </h3>
              </div>
              <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--border)' }}>
                <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--parchment)' }}>
                      {result.previewColumns.map(col => (
                        <th key={col} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--ink-secondary)', whiteSpace: 'nowrap', borderBottom: '1px solid var(--border)' }}>
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.preview.map((row, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--parchment)' }}>
                        {result.previewColumns.map(col => (
                          <td key={col} style={{ padding: '7px 12px', whiteSpace: 'nowrap', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {String(row[col] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 저장 폼 */}
              {!saved && (
                <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid var(--border)' }}>
                  <h4 style={{ margin: '0 0 14px', fontSize: '14px', fontWeight: 600, color: 'var(--ink)' }}>결과 저장</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                    <div>
                      <label className="label">표준화 이름</label>
                      <input className="input" value={saveForm.standardized_name} onChange={e => setSaveForm(f => ({ ...f, standardized_name: e.target.value }))} placeholder="결합_결과_v1" />
                    </div>
                    <div>
                      <label className="label">카테고리</label>
                      <input className="input" value={saveForm.category} onChange={e => setSaveForm(f => ({ ...f, category: e.target.value }))} />
                    </div>
                    <div>
                      <label className="label">프로젝트</label>
                      <input className="input" value={saveForm.project_name} onChange={e => setSaveForm(f => ({ ...f, project_name: e.target.value }))} />
                    </div>
                    <div>
                      <label className="label">태그 (쉼표 구분)</label>
                      <input className="input" value={saveForm.tags} onChange={e => setSaveForm(f => ({ ...f, tags: e.target.value }))} />
                    </div>
                  </div>
                  <div style={{ marginBottom: '16px' }}>
                    <label className="label">설명</label>
                    <input className="input" value={saveForm.description} onChange={e => setSaveForm(f => ({ ...f, description: e.target.value }))} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button className="btn-primary" onClick={handleSave} disabled={saving}>
                      {saving ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Save size={14} />}
                      창고에 저장
                    </button>
                  </div>
                </div>
              )}
              {saved && (
                <div style={{ marginTop: '16px', padding: '12px 16px', borderRadius: '10px', background: '#f0fdf4', fontSize: '14px', color: '#34c759', fontWeight: 500 }}>
                  ✓ 창고에 저장되었습니다.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
