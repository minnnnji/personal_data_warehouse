import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, X } from 'lucide-react'

export interface ToastMessage {
  id: number
  type: 'success' | 'error'
  message: string
}

let toastId = 0
const listeners: ((msg: ToastMessage) => void)[] = []

export const toast = {
  success: (message: string) => listeners.forEach(fn => fn({ id: ++toastId, type: 'success', message })),
  error: (message: string) => listeners.forEach(fn => fn({ id: ++toastId, type: 'error', message })),
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  useEffect(() => {
    const handler = (msg: ToastMessage) => {
      setToasts(prev => [...prev, msg])
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== msg.id)), 4000)
    }
    listeners.push(handler)
    return () => { const i = listeners.indexOf(handler); if (i !== -1) listeners.splice(i, 1) }
  }, [])

  const remove = (id: number) => setToasts(prev => prev.filter(t => t.id !== id))

  if (!toasts.length) return null

  return (
    <div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {toasts.map(t => (
        <div
          key={t.id}
          className="fade-in"
          style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '14px 16px', borderRadius: '14px',
            background: t.type === 'success' ? '#f0fdf4' : '#fff2f2',
            border: `1px solid ${t.type === 'success' ? '#34c759' : '#ff3b30'}30`,
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
            minWidth: '280px', maxWidth: '380px',
          }}
        >
          {t.type === 'success'
            ? <CheckCircle size={16} style={{ color: '#34c759', flexShrink: 0 }} />
            : <XCircle size={16} style={{ color: '#ff3b30', flexShrink: 0 }} />}
          <span style={{ flex: 1, fontSize: '14px', color: 'var(--ink)', letterSpacing: '-0.2px' }}>{t.message}</span>
          <button onClick={() => remove(t.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--ink-tertiary)', display: 'flex' }}>
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
