import { useState } from 'react'
import UploadScreen from './components/UploadScreen'
import AuditScreen from './components/AuditScreen'
import { AuditResponse, UploadResponse } from './services/api'

type Screen = 'upload' | 'audit'

export default function App() {
  const [screen, setScreen] = useState<Screen>('upload')
  const [uploadData, setUploadData] = useState<UploadResponse | null>(null)
  const [auditData, setAuditData] = useState<AuditResponse | null>(null)

  const handleUploadComplete = (data: UploadResponse) => {
    setUploadData(data)
  }

  const handleAuditComplete = (data: AuditResponse) => {
    setAuditData(data)
    setScreen('audit')
  }

  const reset = () => {
    setScreen('upload')
    setAuditData(null)
    setUploadData(null)
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-700/60 bg-slate-900/80 backdrop-blur px-8 py-4 flex items-center gap-4 sticky top-0 z-40">
        <button onClick={reset} className="flex items-center gap-1 group">
          <span className="text-2xl font-bold text-white group-hover:opacity-80 transition-opacity">Fair</span>
          <span className="text-2xl font-bold text-red-400 group-hover:opacity-80 transition-opacity">Lens</span>
        </button>
        <span className="text-slate-500 text-sm hidden sm:block">Pre-training bias auditor</span>
        <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-blue-950/60 border border-blue-700/50 rounded-full text-blue-300 text-xs font-medium">
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          Powered by Vertex AI
        </span>

        {screen === 'audit' && auditData && (
          <div className="flex items-center gap-3 ml-4">
            <span className="text-slate-600">·</span>
            <span className="text-slate-400 text-sm truncate max-w-xs">{uploadData?.session_id.slice(0, 8)}…</span>
          </div>
        )}

        {screen === 'audit' && (
          <button
            onClick={reset}
            className="ml-auto text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-1"
          >
            ← New Upload
          </button>
        )}
      </header>

      <main className="p-6 md:p-8">
        {screen === 'upload' && (
          <UploadScreen
            onUploadComplete={handleUploadComplete}
            onAuditComplete={handleAuditComplete}
            uploadData={uploadData}
            auditData={auditData}
          />
        )}
        {screen === 'audit' && uploadData && (
          <AuditScreen
            uploadData={uploadData}
            initialAuditData={auditData}
            onAuditComplete={setAuditData}
          />
        )}
      </main>
    </div>
  )
}
