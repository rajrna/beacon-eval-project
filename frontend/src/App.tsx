import { Routes, Route, Navigate } from 'react-router-dom'
import { MsalProvider, AuthenticatedTemplate, UnauthenticatedTemplate } from '@azure/msal-react'
import { useEffect } from 'react'
import { msalInstance, IS_AUTH_ENABLED } from '@/lib/auth/config'
import { useAuth } from '@/lib/auth/useAuth'
import { setTokenGetter } from '@/lib/api/client'
import { Shell } from '@/components/layout/Shell'
import Institutions from '@/pages/Institutions'
import { Programs, Agents, Datasets, Judges, TraceBrowser, Settings } from '@/pages/Other'
import Chat from '@/pages/Chat'
import DatasetDetail from '@/pages/DatasetDetail'
import AgentDetail from '@/pages/AgentDetail'
import AgentVersionDetail from '@/pages/AgentVersionDetail'
import Runs from '@/pages/Runs'
import RunDetail from '@/pages/RunDetail'
import TraceDetail from '@/pages/TraceDetail'
import SmeQueue from '@/pages/SmeQueue'

function TokenSync() {
  const { getToken } = useAuth()
  useEffect(() => { setTokenGetter(getToken) }, [getToken])
  return null
}

function AppRoutes() {
  return (
    <Shell>
      <TokenSync />
      <Routes>
        <Route path="/" element={<Navigate to="/institutions" replace />} />
        <Route path="/institutions" element={<Institutions />} />
        <Route path="/programs" element={<Programs />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/agents/:id" element={<AgentDetail />} />
        <Route path="/agents/:id/versions/:versionId" element={<AgentVersionDetail />} />
        <Route path="/datasets" element={<Datasets />} />
        <Route path="/datasets/:id" element={<DatasetDetail />} />
        <Route path="/judges" element={<Judges />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/runs/:id" element={<RunDetail />} />
        <Route path="/traces" element={<TraceBrowser />} />
        <Route path="/traces/:id" element={<TraceDetail />} />
        <Route path="/sme/queue" element={<SmeQueue />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  )
}

function LoginPage() {
  const { login } = useAuth()
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-6">
        <div className="h-16 w-16 rounded-2xl bg-beacon-600 flex items-center justify-center mx-auto">
          <span className="text-white font-bold text-2xl">B</span>
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Beacon</h1>
          <p className="mt-2 text-gray-500">Student Agent Evaluation Platform</p>
        </div>
        <button
          onClick={login}
          className="bg-beacon-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-beacon-700 transition-colors"
        >
          Sign in with Microsoft
        </button>
      </div>
    </div>
  )
}

export default function App() {
  if (!IS_AUTH_ENABLED) {
    return <AppRoutes />
  }

  return (
    <MsalProvider instance={msalInstance}>
      <AuthenticatedTemplate>
        <AppRoutes />
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <LoginPage />
      </UnauthenticatedTemplate>
    </MsalProvider>
  )
}
