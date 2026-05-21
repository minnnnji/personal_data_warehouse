import { useState, useEffect } from 'react'
import { GitBranch, RefreshCw } from 'lucide-react'
import { getLineage, type LineageNode, type LineageEdge } from '../api'
import { toast } from '../components/Toast'

export default function Lineage() {
  const [nodes, setNodes] = useState<LineageNode[]>([])
  const [edges, setEdges] = useState<LineageEdge[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const data = await getLineage()
      setNodes(data.nodes)
      setEdges(data.edges)
    } catch {
      toast.error('Lineage 데이터를 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '80px 0' }}>
      <span className="spinner" style={{ width: 28, height: 28 }} />
    </div>
  )

  if (!nodes.length) return (
    <div>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px' }}>Lineage</h1>
        <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-tertiary)' }}>데이터 계보 그래프</p>
      </div>
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <GitBranch size={40} style={{ color: 'var(--ink-tertiary)', margin: '0 auto 16px' }} />
        <p style={{ color: 'var(--ink-tertiary)', fontSize: '15px' }}>아직 Lineage 데이터가 없습니다.</p>
        <p style={{ color: 'var(--ink-tertiary)', fontSize: '13px', marginTop: '6px' }}>데이터 결합 후 계보가 생성됩니다.</p>
      </div>
    </div>
  )

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px' }}>Lineage</h1>
          <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-tertiary)' }}>
            {nodes.length}개 노드 · {edges.length}개 관계
          </p>
        </div>
        <button className="btn-secondary" onClick={load}>
          <RefreshCw size={14} />
          새로고침
        </button>
      </div>

      {/* 간단한 텍스트 기반 lineage 표시 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {edges.map((edge, i) => {
          const from = nodes.find(n => n.id === edge.from)
          const to = nodes.find(n => n.id === edge.to)
          return (
            <div key={i} className="card fade-in" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ flex: 1, padding: '12px 16px', borderRadius: '10px', background: 'var(--parchment)', textAlign: 'center' }}>
                <p style={{ margin: 0, fontSize: '13px', fontWeight: 600, color: 'var(--ink)' }}>{from?.label ?? edge.from}</p>
              </div>
              <div style={{ textAlign: 'center', padding: '0 8px' }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--action-blue)', marginBottom: '4px', whiteSpace: 'nowrap' }}>
                  {edge.label}
                </div>
                <div style={{ color: 'var(--ink-tertiary)', fontSize: '20px' }}>→</div>
              </div>
              <div style={{ flex: 1, padding: '12px 16px', borderRadius: '10px', background: 'rgba(0,102,204,0.06)', textAlign: 'center', border: '1px solid rgba(0,102,204,0.15)' }}>
                <p style={{ margin: 0, fontSize: '13px', fontWeight: 600, color: 'var(--action-blue)' }}>{to?.label ?? edge.to}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
