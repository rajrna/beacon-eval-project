import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Lock, Unlock, PlayCircle, Copy, Check } from 'lucide-react'
import { useAgentVersion, useAgent } from '@/lib/api/hooks'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import type { Paginated, EvalRun } from '@/lib/api/types'
import {
  Button, Card, CardHeader, CardTitle, CardContent,
  Badge, Spinner, PageHeader, EmptyState,
} from '@/components/ui'
import { formatDate, formatScore, formatCost, statusColor, cn } from '@/lib/utils'
import { RunTriggerModal } from '@/components/eval/RunTriggerModal'

function useVersionRuns(agentVersionId: string) {
  return useQuery({
    queryKey: ['version-runs', agentVersionId],
    queryFn: () =>
      api.get<Paginated<EvalRun>>(`/v1/runs?agent_version_id=${agentVersionId}&limit=20`)
        .catch(() => ({ items: [], total: 0, limit: 20, offset: 0, has_more: false })),
    enabled: Boolean(agentVersionId),
  })
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className="text-gray-500 hover:text-gray-300 transition-colors">
      {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
    </button>
  )
}

export default function AgentVersionDetail() {
  const { id, versionId } = useParams<{ id: string; versionId: string }>()
  const navigate = useNavigate()
  const [runModalOpen, setRunModalOpen] = useState(false)

  const { data: agent } = useAgent(id!)
  const { data: version, isLoading } = useAgentVersion(id!, versionId!)
  const { data: runs } = useVersionRuns(versionId!)

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  if (!version) return <div className="text-center py-20 text-gray-500">Version not found</div>

  const passRates = runs?.items
    ?.filter((r: EvalRun) => r.pass_rate != null)
    .map((r: EvalRun) => r.pass_rate as number) ?? []
  const avgPassRate = passRates.length
    ? passRates.reduce((a, b) => a + b, 0) / passRates.length
    : null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(`/agents/${id}`)} className="text-gray-500 hover:text-gray-300">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <PageHeader
          title={`${agent?.name ?? 'Agent'} — v${version.version_number}`}
          description={`${version.model_id} · Created ${formatDate(version.created_at)}`}
          action={
            <Button onClick={() => setRunModalOpen(true)}>
              <PlayCircle className="h-4 w-4" /> Run Eval with this Version
            </Button>
          }
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: 'Version', value: <span className="text-xl font-bold font-mono">v{version.version_number}</span> },
          { label: 'Model', value: <code className="text-sm text-gray-300">{version.model_id}</code> },
          { label: 'Temperature', value: <span className="text-xl font-bold">{version.temperature}</span> },
          { label: 'Max Tokens', value: <span className="text-xl font-bold">{version.max_tokens}</span> },
          { label: 'Status', value: version.is_locked
            ? <div className="flex items-center gap-1.5 text-sm text-gray-500"><Lock className="h-4 w-4" /> Locked</div>
            : <div className="flex items-center gap-1.5 text-sm text-green-400"><Unlock className="h-4 w-4" /> Editable</div>
          },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardContent className="py-3">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              {value}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* System prompt */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>System Prompt</CardTitle>
                <CopyButton text={version.system_prompt} />
              </div>
            </CardHeader>
            <CardContent>
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono leading-relaxed bg-white/3 rounded-lg p-4 border border-white/5 max-h-96 overflow-y-auto">
                {version.system_prompt}
              </pre>
            </CardContent>
          </Card>

          {version.notes && (
            <Card>
              <CardHeader><CardTitle>Version Notes</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm text-gray-400 italic">{version.notes}</p>
              </CardContent>
            </Card>
          )}

          {version.tool_definitions && (
            <Card>
              <CardHeader><CardTitle>Tool Definitions</CardTitle></CardHeader>
              <CardContent>
                <pre className="text-xs text-gray-400 bg-white/3 rounded-lg p-3 overflow-x-auto border border-white/5">
                  {JSON.stringify(version.tool_definitions, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Run history + stats */}
        <div className="space-y-4">
          {/* Aggregate */}
          {runs?.items && runs.items.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Performance</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Avg Pass Rate</p>
                    <p className={cn('text-3xl font-bold',
                      avgPassRate == null ? 'text-gray-600' :
                      avgPassRate >= 0.8 ? 'text-green-400' :
                      avgPassRate >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                    )}>
                      {avgPassRate != null ? formatScore(avgPassRate) : '—'}
                    </p>
                    {avgPassRate != null && (
                      <div className="w-full bg-white/5 rounded-full h-1.5 mt-2">
                        <div
                          className={cn('h-1.5 rounded-full',
                            avgPassRate >= 0.8 ? 'bg-green-500' :
                            avgPassRate >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                          )}
                          style={{ width: `${avgPassRate * 100}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/5">
                    <div>
                      <p className="text-xs text-gray-500">Total Runs</p>
                      <p className="text-lg font-bold text-gray-200">{runs.total}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Succeeded</p>
                      <p className="text-lg font-bold text-green-400">
                        {runs.items.filter((r: EvalRun) => r.status === 'succeeded').length}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Run list */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Eval Runs</CardTitle>
                <Button size="sm" variant="outline" onClick={() => setRunModalOpen(true)}>
                  <PlayCircle className="h-3.5 w-3.5" /> Run
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {!runs?.items?.length ? (
                <div className="px-6 py-8">
                  <EmptyState
                    title="No runs yet"
                    description="Run an eval to see results for this version."
                    action={<Button size="sm" onClick={() => setRunModalOpen(true)}>Run Eval</Button>}
                  />
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {runs.items.map((run: EvalRun) => (
                    <div
                      key={run.id}
                      className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors"
                      onClick={() => navigate(`/runs/${run.id}`)}
                    >
                      <div>
                        <p className="text-xs font-mono text-gray-400">{run.id.slice(0, 8)}…</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={cn('text-xs px-1.5 py-0.5 rounded-full', statusColor(run.status))}>
                            {run.status}
                          </span>
                          <span className="text-xs text-gray-600">{run.total_examples ?? '?'} examples</span>
                        </div>
                      </div>
                      <div className="text-right">
                        {run.pass_rate != null && (
                          <p className={cn('text-sm font-bold',
                            run.pass_rate >= 0.8 ? 'text-green-400' :
                            run.pass_rate >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                          )}>
                            {formatScore(run.pass_rate)}
                          </p>
                        )}
                        <p className="text-xs text-gray-600 mt-0.5">{formatCost(run.total_cost_usd)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <RunTriggerModal
        open={runModalOpen}
        onClose={() => setRunModalOpen(false)}
        onSuccess={runId => navigate(`/runs/${runId}`)}
      />
    </div>
  )
}
