import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlayCircle, Plus } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useTriggerEvalRun, useJudges } from '@/lib/api/hooks'
import { api } from '@/lib/api/client'
import type { Paginated, EvalRun } from '@/lib/api/types'
import {
  Button, Card, PageHeader, EmptyState, Badge,
  Table, Thead, Tbody, Th, Td, Dialog, Select, Spinner,
} from '@/components/ui'
import { formatDate, formatScore, formatCost, statusColor, cn } from '@/lib/utils'

function useRecentRuns() {
  return useQuery({
    queryKey: ['runs'],
    queryFn: () => api.get<Paginated<EvalRun>>('/v1/runs?limit=50'),
  })
}

export default function Runs() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ agent_version_id: '', dataset_id: '', judge_version_ids: [] as string[] })
  const { data, isLoading } = useRecentRuns()
  const { data: judges } = useJudges()
  const trigger = useTriggerEvalRun()

  const handleTrigger = async () => {
    await trigger.mutateAsync(form)
    setOpen(false)
  }

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>

  return (
    <div>
      <PageHeader
        title="Eval Runs"
        description="Evaluation run history and results"
        action={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />New Run</Button>}
      />

      <Card>
        {!data?.items?.length ? (
          <div className="px-6 py-12">
            <EmptyState
              title="No eval runs yet"
              description="Trigger your first eval run to see results here."
              action={<Button onClick={() => setOpen(true)}>Trigger Eval Run</Button>}
            />
          </div>
        ) : (
          <Table>
            <Thead>
              <tr>
                <Th>Run ID</Th>
                <Th>Status</Th>
                <Th>Pass Rate</Th>
                <Th>Examples</Th>
                <Th>Cost</Th>
                <Th>Triggered</Th>
              </tr>
            </Thead>
            <Tbody>
              {data.items.map(run => (
                <tr
                  key={run.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => navigate(`/runs/${run.id}`)}
                >
                  <Td>
                    <div className="flex items-center gap-2">
                      <PlayCircle className="h-4 w-4 text-gray-400" />
                      <code className="text-xs text-gray-600">{run.id.slice(0, 8)}…</code>
                    </div>
                  </Td>
                  <Td>
                    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', statusColor(run.status))}>
                      {run.status}
                    </span>
                  </Td>
                  <Td>
                    {run.pass_rate != null ? (
                      <span className={run.pass_rate >= 0.8 ? 'text-green-700 font-medium' : 'text-red-700 font-medium'}>
                        {formatScore(run.pass_rate)}
                      </span>
                    ) : '—'}
                  </Td>
                  <Td>{run.total_examples ?? '—'}</Td>
                  <Td className="text-gray-500">{formatCost(run.total_cost_usd)}</Td>
                  <Td className="text-gray-500">{formatDate(run.created_at)}</Td>
                </tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} title="Trigger Eval Run">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Agent Version ID</label>
            <input
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="UUID of the agent version to evaluate"
              value={form.agent_version_id}
              onChange={e => setForm(f => ({ ...f, agent_version_id: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Dataset ID</label>
            <input
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="UUID of the dataset to run against"
              value={form.dataset_id}
              onChange={e => setForm(f => ({ ...f, dataset_id: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Judge Version IDs</label>
            <input
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Comma-separated UUIDs"
              onChange={e => setForm(f => ({ ...f, judge_version_ids: e.target.value.split(',').map(s => s.trim()).filter(Boolean) }))}
            />
            <p className="text-xs text-gray-500 mt-1">Available judges: {judges?.items?.map(j => j.slug).join(', ')}</p>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={handleTrigger} loading={trigger.isPending}>Trigger Run</Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
