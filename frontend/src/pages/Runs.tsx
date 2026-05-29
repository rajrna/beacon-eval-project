import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlayCircle, Plus, RefreshCw } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import type { Paginated, EvalRun } from '@/lib/api/types'
import {
  Button, Card, PageHeader, EmptyState, Badge,
  Table, Thead, Tbody, Th, Td, Spinner,
} from '@/components/ui'
import { formatDate, formatScore, formatCost, formatLatency, statusColor, cn } from '@/lib/utils'
import { RunTriggerModal } from '@/components/eval/RunTriggerModal'

function useRecentRuns() {
  return useQuery({
    queryKey: ['runs'],
    queryFn: () => api.get<Paginated<EvalRun>>('/v1/runs?limit=50'),
    refetchInterval: (query) => {
      const hasActive = query.state.data?.items?.some(
        r => r.status === 'queued' || r.status === 'running'
      )
      return hasActive ? 3000 : false
    },
  })
}

export default function Runs() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const { data, isLoading, refetch } = useRecentRuns()

  const handleRunSuccess = (runId: string) => {
    qc.invalidateQueries({ queryKey: ['runs'] })
    navigate(`/runs/${runId}`)
  }

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>

  return (
    <div>
      <PageHeader
        title="Eval Runs"
        description="Evaluation run history and results"
        action={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button onClick={() => setModalOpen(true)}>
              <Plus className="h-4 w-4" /> New Run
            </Button>
          </div>
        }
      />

      <Card>
        {!data?.items?.length ? (
          <div className="px-6 py-12">
            <EmptyState
              title="No eval runs yet"
              description="Trigger your first eval run to see results here."
              action={<Button onClick={() => setModalOpen(true)}>Trigger Eval Run</Button>}
            />
          </div>
        ) : (
          <Table>
            <Thead>
              <tr>
                <Th>Run</Th>
                <Th>Status</Th>
                <Th>Pass Rate</Th>
                <Th>Examples</Th>
                <Th>Judges</Th>
                <Th>Cost</Th>
                <Th>Duration</Th>
                <Th>Triggered</Th>
              </tr>
            </Thead>
            <Tbody>
              {data.items.map(run => (
                <tr
                  key={run.id}
                  className="cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => navigate(`/runs/${run.id}`)}
                >
                  <Td>
                    <div className="flex items-center gap-2">
                      <PlayCircle className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      <code className="text-xs text-gray-600">{run.id.slice(0, 8)}…</code>
                    </div>
                  </Td>
                  <Td>
                    <span className={cn(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium gap-1',
                      statusColor(run.status)
                    )}>
                      {(run.status === 'queued' || run.status === 'running') && (
                        <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
                      )}
                      {run.status}
                    </span>
                  </Td>
                  <Td>
                    {run.pass_rate != null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-100 rounded-full h-1.5">
                          <div
                            className={cn('h-1.5 rounded-full',
                              run.pass_rate >= 0.8 ? 'bg-green-500' :
                              run.pass_rate >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                            )}
                            style={{ width: `${run.pass_rate * 100}%` }}
                          />
                        </div>
                        <span className={cn('font-medium text-sm',
                          run.pass_rate >= 0.8 ? 'text-green-700' :
                          run.pass_rate >= 0.6 ? 'text-yellow-700' : 'text-red-700'
                        )}>
                          {formatScore(run.pass_rate)}
                        </span>
                      </div>
                    ) : '—'}
                  </Td>
                  <Td className="text-gray-600">{run.total_examples ?? '—'}</Td>
                  <Td><Badge variant="info">{run.judge_version_ids.length}</Badge></Td>
                  <Td className="text-gray-500 text-xs">{formatCost(run.total_cost_usd)}</Td>
                  <Td className="text-gray-500 text-xs">
                    {run.started_at && run.completed_at
                      ? formatLatency(new Date(run.completed_at).getTime() - new Date(run.started_at).getTime())
                      : '—'}
                  </Td>
                  <Td className="text-gray-500 text-xs">{formatDate(run.created_at)}</Td>
                </tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>

      <RunTriggerModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={handleRunSuccess}
      />
    </div>
  )
}
