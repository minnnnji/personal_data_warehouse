import { useState, useRef } from 'react'
import { Upload as UploadIcon, CheckCircle, AlertCircle, X } from 'lucide-react'
import { uploadFile, confirmUpload, type UploadAnalysisResult } from '../api'
import { toast } from '../components/Toast'

interface Props {
  onUploaded?: () => void
}

export default function Upload({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<UploadAnalysisResult | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 폼 상태
  const [form, setForm] = useState({
    standardized_name: '',
    product_name: '',
    category: '',
    project_name: '',
    description: '',
    tags: '',
    user_answer: '',
  })

  const handleFile = async (file: File) => {
    setSaved(false)
    setAnalysis(null)
    setAnalyzing(true)
    try {
      const result = await uploadFile(file)
      setAnalysis(result)
      setForm({
        standardized_name: result.standardized_name ?? '',
        product_name: result.product_name ?? '',
        category: result.category ?? '',
        project_name: result.project_name ?? '',
        description: result.description ?? '',
        tags: (result.tags ?? []).join(', '),
        user_answer: '',
      })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '파일 분석에 실패했습니다.'
      toast.error(msg)
    } finally {
      setAnalyzing(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const handleConfirm = async () => {
    if (!analysis) return
    setSaving(true)
    try {
      await confirmUpload({
        file_id: analysis.file_id,
        standardized_name: form.standardized_name,
        product_name: form.product_name,
        category: form.category,
        project_name: form.project_name,
        description: form.description,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
        user_answer: form.user_answer || undefined,
      })
      toast.success('파일이 창고에 저장되었습니다.')
      setSaved(true)
      setAnalysis(null)
      onUploaded?.()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '저장에 실패했습니다.'
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  const reset = () => {
    setAnalysis(null)
    setSaved(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px' }}>
          파일 업로드
        </h1>
        <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-tertiary)' }}>
          CSV, Excel, PKL, Parquet 파일을 업로드하면 AI가 메타데이터를 자동으로 분석합니다.
        </p>
      </div>

      {/* 성공 메시지 */}
      {saved && (
        <div className="fade-in" style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 20px', borderRadius: '14px', background: '#f0fdf4', border: '1px solid #34c75930', marginBottom: '20px' }}>
          <CheckCircle size={18} style={{ color: '#34c759' }} />
          <span style={{ fontSize: '14px', color: 'var(--ink)' }}>파일이 성공적으로 저장되었습니다.</span>
          <button onClick={reset} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-tertiary)', display: 'flex' }}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* 드롭존 */}
      {!analysis && !analyzing && (
        <div
          className={`card`}
          style={{
            border: `2px dashed ${dragging ? 'var(--action-blue)' : 'var(--border)'}`,
            background: dragging ? 'rgba(0,102,204,0.04)' : 'var(--surface)',
            cursor: 'pointer',
            textAlign: 'center',
            padding: '60px 40px',
            transition: 'all 0.15s',
          }}
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadIcon size={40} style={{ color: dragging ? 'var(--action-blue)' : 'var(--ink-tertiary)', margin: '0 auto 16px' }} />
          <p style={{ margin: '0 0 6px', fontSize: '16px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.3px' }}>
            파일을 드래그하거나 클릭하여 선택
          </p>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--ink-tertiary)' }}>
            CSV, XLSX, PKL, Parquet 지원
          </p>
          <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls,.pkl,.parquet" style={{ display: 'none' }} onChange={onFileChange} />
        </div>
      )}

      {/* 분석 중 */}
      {analyzing && (
        <div className="card fade-in" style={{ textAlign: 'center', padding: '60px 40px' }}>
          <span className="spinner" style={{ width: 32, height: 32, margin: '0 auto 16px', display: 'block' }} />
          <p style={{ margin: 0, fontSize: '15px', color: 'var(--ink-secondary)' }}>AI가 파일을 분석 중입니다...</p>
        </div>
      )}

      {/* 분석 결과 폼 */}
      {analysis && (
        <div className="fade-in">
          {/* 파일 정보 요약 */}
          <div className="card" style={{ marginBottom: '16px', background: 'var(--parchment)', borderStyle: 'dashed' }}>
            <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
              <div>
                <span className="label" style={{ marginBottom: 2 }}>파일명</span>
                <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--ink)' }}>{analysis.original_filename}</p>
              </div>
              <div>
                <span className="label" style={{ marginBottom: 2 }}>크기</span>
                <p style={{ margin: 0, fontSize: '14px', color: 'var(--ink)' }}>{analysis.row_count.toLocaleString()} 행 × {analysis.col_count} 열</p>
              </div>
              <div>
                <span className="label" style={{ marginBottom: 2 }}>형식</span>
                <p style={{ margin: 0, fontSize: '14px', color: 'var(--ink)', textTransform: 'uppercase' }}>{analysis.file_format}</p>
              </div>
              {analysis.pkl_count && analysis.pkl_count > 1 && (
                <div>
                  <span className="label" style={{ marginBottom: 2 }}>PKL 내 DataFrame</span>
                  <p style={{ margin: 0, fontSize: '14px', color: 'var(--action-blue)', fontWeight: 600 }}>{analysis.pkl_count}개 → 개별 저장</p>
                </div>
              )}
            </div>
          </div>

          {/* LLM 불확실 질문 */}
          {analysis.uncertain && analysis.question_for_user && (
            <div style={{ display: 'flex', gap: '10px', padding: '14px 20px', borderRadius: '14px', background: '#fffbf0', border: '1px solid #ff950030', marginBottom: '16px' }}>
              <AlertCircle size={18} style={{ color: '#ff9500', flexShrink: 0, marginTop: '1px' }} />
              <div style={{ flex: 1 }}>
                <p style={{ margin: '0 0 10px', fontSize: '14px', color: 'var(--ink)' }}>{analysis.question_for_user}</p>
                <input
                  className="input"
                  placeholder="답변을 입력하세요"
                  value={form.user_answer}
                  onChange={e => setForm(f => ({ ...f, user_answer: e.target.value }))}
                />
              </div>
            </div>
          )}

          {/* 메타데이터 편집 폼 */}
          <div className="card">
            <h2 style={{ margin: '0 0 20px', fontSize: '17px', fontWeight: 600, letterSpacing: '-0.3px' }}>
              메타데이터 확인 및 수정
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label className="label">표준화 이름</label>
                <input className="input" value={form.standardized_name} onChange={e => setForm(f => ({ ...f, standardized_name: e.target.value }))} placeholder="예: PR_A제품_raw_iqc_v1" />
              </div>
              <div>
                <label className="label">제품명</label>
                <input className="input" value={form.product_name} onChange={e => setForm(f => ({ ...f, product_name: e.target.value }))} placeholder="예: A제품, B소재" />
              </div>
              <div>
                <label className="label">카테고리</label>
                <input className="input" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} placeholder="예: 품질, 생산, 영업" />
              </div>
              <div>
                <label className="label">프로젝트</label>
                <input className="input" value={form.project_name} onChange={e => setForm(f => ({ ...f, project_name: e.target.value }))} placeholder="예: Smart DoE" />
              </div>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label className="label">설명</label>
              <textarea
                className="input"
                style={{ height: '80px', resize: 'vertical' }}
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="이 데이터가 무엇인지 설명하세요."
              />
            </div>
            <div style={{ marginBottom: '24px' }}>
              <label className="label">태그 (쉼표로 구분)</label>
              <input className="input" value={form.tags} onChange={e => setForm(f => ({ ...f, tags: e.target.value }))} placeholder="lot_id, cd, thickness" />
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button className="btn-secondary" onClick={reset}>취소</button>
              <button className="btn-primary" onClick={handleConfirm} disabled={saving}>
                {saving ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <CheckCircle size={14} />}
                창고에 저장
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
