import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AlertTriangle, Clock, CheckCircle, Filter } from 'lucide-react'
import { useSmeQueue, useAcknowledgeQueueItem, useResolveQueueItem } from '@/lib/api/hooks'
import type { QueueItem } from '@/lib/api/types'
import {
  Button, Card, CardContent, PageHeader, EmptyState, Badge, Spinner,
  Table, Thead, Tbody, Th, Td, Dialog, Textarea,
} from '@/components/ui'
import { formatRelative, formatDate, priorityColor, cn } from '@/lib/utils'

function PriorityIcon({ priority }: { priority: string }) {
  if (priority === 'crisis') return <AlertTriangle className="h-4 w-4 text-red-500" />
  if (priority === 'concerning') return <Clock className="h-4 w-4 text-orange-500" />
  return <CheckCircle className="h-4 w-4 text-blue-500" />
}

export default function SmeQueue() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [statusFilter, setStatusFilter] = useState(params.get('status') || 'queued')
  const [priorityFilter, setPriorityFilter] = useState(params.get('priority') || '')
  const [resolveItem, setResolveItem] = useState<QueueItem | null>(null)
  const [resolveNotes, setResolveNotes] = useState('')

  const { data, isLoading, refetch } = useSmeQueue(statusFilter || undefined, priorityFilter || undefined)
  const acknowledge = useAcknowledgeQueueItem()
  const resolve = useResolveQueueItem()

  // Keyboard shortcuts
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
    if (e.key === 'r') refetch()
  }, [refetch])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const handleAcknowledge = async (item: QueueItem) => {
    await acknowledge.mutateAsync({ id: item.id })
  }

  const handleResolve = async () => {
    if (!resolveItem) return
    await resolve.mutateAsync({ id: resolveItem.id, resolution_notes: resolveNotes })
    setResolveItem(null)
    setResolveNotes('')
  }

  const crisisItems = data?.items?.filter(i => i.priority === 'crisis') ?? []

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>

  return (
    <div>
      <PageHeader
        title="SME Review Queue"
        description="Safety-flagged traces requiring human review"
      />

      {/* Crisis alert banner */}
      {crisisItems.length > 0 && statusFilter === 'queued' && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0" />
          <div>
            <p className="text-sm font-semibold text-red-800">
              {crisisItems.length} crisis-priority {crisisItems.length === 1 ? 'trace' : 'traces'} require immediate review (15-min SLA)
            </p>
            <p className="text-xs text-red-600 mt-0.5">
              Oldest: {formatRelative(crisisItems[0]?.created_at)}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All statuses</option>
          <option value="queued">Queued</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
        <select
          value={priorityFilter}
          onChange={e => setPriorityFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All priorities</option>
          <option value="crisis">Crisis</option>
          <option value="concerning">Concerning</option>
          <option value="routine">Routine</option>
        </select>
        <span className="text-xs text-gray-400 self-center ml-2">Press R to refresh</span>
      </div>

      <Card>
        {!data?.items?.length ? (
          <CardContent>
            <EmptyState title="Queue is clear" description="No traces matching this filter." />
          </CardContent>
        ) : (
          <Table>
            <Thead>
              <tr>
                <Th>Priority</Th>
                <Th>Trace</Th>
                <Th>Flags</Th>
                <Th>SLA</Th>
                <Th>Age</Th>
                <Th>Actions</Th>
              </tr>
            </Thead>
            <Tbody>
              {data.items.map(item => (
                <tr
                  key={item.id}
                  className={cn('hover:bg-gray-50', item.sla_breached && 'bg-red-50')}
                >
                  <Td>
                    <div className="flex items-center gap-1.5">
                      <PriorityIcon priority={item.priority} />
                      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium border', priorityColor(item.priority))}>
                        {item.priority}
                      </span>
                      {item.sla_breached && (
                        <span className="text-xs text-red-600 font-medium">SLA breached</span>
                      )}
                    </div>
                  </Td>
                  <Td>
                    <button
                      className="text-beacon-600 hover:underline text-sm font-mono"
                      onClick={() => navigate(`/traces/${item.trace_id}`)}
                    >
                      {item.trace_id.slice(0, 8)}…
                    </button>
                  </Td>
                  <Td>
                    <div className="flex gap-1 flex-wrap">
                      {item.trace?.safety_flags?.map(f => (
                        <span key={f} className="text-xs bg-red-50 text-red-700 px-1.5 py-0.5 rounded border border-red-100">{f}</span>
                      ))}
                    </div>
                  </Td>
                  <Td>
                    {item.sla_deadline ? (
                      <span className={cn('text-xs', new Date(item.sla_deadline) < new Date() ? 'text-red-600 font-medium' : 'text-gray-500')}>
                        {formatDate(item.sla_deadline)}
                      </span>
                    ) : '—'}
                  </Td>
                  <Td className="text-gray-500 text-xs">{formatRelative(item.created_at)}</Td>
                  <Td>
                    <div className="flex gap-2">
                      {item.status === 'queued' && (
                        <Button size="sm" variant="outline" onClick={() => handleAcknowledge(item)} loading={acknowledge.isPending}>
                          Acknowledge
                        </Button>
                      )}
                      {item.status === 'acknowledged' && (
                        <Button size="sm" onClick={() => setResolveItem(item)}>
                          Resolve
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" onClick={() => navigate(`/traces/${item.trace_id}`)}>
                        View Trace
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>

      <Dialog open={Boolean(resolveItem)} onClose={() => setResolveItem(null)} title="Resolve Queue Item">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Provide resolution notes before closing this item.
          </p>
          <Textarea
            label="Resolution notes"
            rows={4}
            value={resolveNotes}
            onChange={e => setResolveNotes(e.target.value)}
            placeholder="Describe what action was taken and why this trace is resolved..."
          />
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setResolveItem(null)}>Cancel</Button>
            <Button onClick={handleResolve} loading={resolve.isPending} disabled={resolveNotes.length < 5}>
              Mark Resolved
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
