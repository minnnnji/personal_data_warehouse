import { useState, useEffect } from 'react'
import { Plus, Trash2, Settings } from 'lucide-react'
import { getConventions, addConvention, deleteConvention, type Convention } from '../api'
import { toast } from '../components/Toast'

const FIELDS = [
  { key: 'domain', label: 'Domain', description: '데이터 도메인 (예: PR, WFR, IQC)' },
  { key: 'data_type', label: 'Data Type', description: '데이터 유형 (예: raw, model, report)' },
  { key: 'stage', label: 'Stage', description: '처리 단계 (예: cleaned, analyzed)' },
]

export default function Convention() {
  const [conventions, setConventions] = useState<Convention[]>([])
  const [loading, setLoading] = useState(true)
  const [addForm, setAddForm] = useState({ field: 'domain', value: '', description: '' })
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    getConventions().then(setConventions).finally(() => setLoading(false))
  }, [])

  const handleAdd = async () => {
    if (!addForm.value.trim()) { toast.error('값을 입력하세요.'); return }
    setAdding(true)
    try {
      const item = await addConvention(addForm)
      setConventions(prev => [...prev, item])
      setAddForm(f => ({ ...f, value: '', description: '' }))
      toast.success('컨벤션이 추가되었습니다.')
    } catch {
      toast.error('추가에 실패했습니다.')
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('이 항목을 삭제하시겠습니까?')) return
    try {
      await deleteConvention(id)
      setConventions(prev => prev.filter(c => c.id !== id))
      toast.success('삭제되었습니다.')
    } catch {
      toast.error('삭제에 실패했습니다.')
    }
  }

  const byField = (field: string) => conventions.filter(c => c.field === field)

  return (
    <div>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px' }}>
          네이밍 컨벤션
        </h1>
        <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-tertiary)' }}>
          파일 표준화 이름 생성에 사용되는 컨벤션을 관리합니다.
        </p>
      </div>

      {/* 설명 배너 */}
      <div style={{ padding: '16px 20px', borderRadius: '14px', background: 'rgba(0,102,204,0.05)', border: '1px solid rgba(0,102,204,0.12)', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
          <Settings size={16} style={{ color: 'var(--action-blue)', marginTop: '2px', flexShrink: 0 }} />
          <div>
            <p style={{ margin: '0 0 4px', fontSize: '14px', fontWeight: 600, color: 'var(--ink)' }}>표준화 이름 형식</p>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--ink-secondary)', fontFamily: 'ui-monospace, monospace' }}>
              {'{domain}_{product_name}_{data_type}_{stage}_v1'}
            </p>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <span className="spinner" style={{ width: 28, height: 28 }} />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '28px' }}>
          {FIELDS.map(({ key, label, description }) => (
            <div key={key} className="card">
              <div style={{ marginBottom: '14px' }}>
                <h3 style={{ margin: '0 0 4px', fontSize: '15px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.2px' }}>
                  {label}
                </h3>
                <p style={{ margin: 0, fontSize: '12px', color: 'var(--ink-tertiary)' }}>{description}</p>
              </div>
              <hr className="divider" style={{ marginBottom: '14px' }} />
              {byField(key).length === 0 ? (
                <p style={{ fontSize: '13px', color: 'var(--ink-tertiary)', textAlign: 'center', padding: '16px 0' }}>
                  항목 없음
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {byField(key).map(c => (
                    <div
                      key={c.id}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', borderRadius: '10px', background: 'var(--parchment)' }}
                    >
                      <div>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)', fontFamily: 'ui-monospace, monospace' }}>{c.value}</span>
                        {c.description && (
                          <span style={{ fontSize: '11px', color: 'var(--ink-tertiary)', marginLeft: '8px' }}>{c.description}</span>
                        )}
                      </div>
                      <button
                        onClick={() => handleDelete(c.id)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-tertiary)', padding: '4px', display: 'flex', borderRadius: '6px' }}
                        onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                        onMouseLeave={e => e.currentTarget.style.color = 'var(--ink-tertiary)'}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 추가 폼 */}
      <div className="card">
        <h3 style={{ margin: '0 0 16px', fontSize: '15px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.2px' }}>
          새 항목 추가
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr auto', gap: '12px', alignItems: 'flex-end' }}>
          <div>
            <label className="label">분류</label>
            <select className="select" value={addForm.field} onChange={e => setAddForm(f => ({ ...f, field: e.target.value }))}>
              {FIELDS.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
            </select>
          </div>
          <div>
            <label className="label">값</label>
            <input
              className="input"
              placeholder="예: PR"
              value={addForm.value}
              onChange={e => setAddForm(f => ({ ...f, value: e.target.value }))}
              onKeyDown={e => e.key === 'Enter' && handleAdd()}
            />
          </div>
          <div>
            <label className="label">설명 (선택)</label>
            <input
              className="input"
              placeholder="예: 포토레지스트"
              value={addForm.description}
              onChange={e => setAddForm(f => ({ ...f, description: e.target.value }))}
              onKeyDown={e => e.key === 'Enter' && handleAdd()}
            />
          </div>
          <button className="btn-primary" onClick={handleAdd} disabled={adding} style={{ height: '42px' }}>
            {adding ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Plus size={14} />}
            추가
          </button>
        </div>
      </div>
    </div>
  )
}
