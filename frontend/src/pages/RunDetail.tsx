import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ChevronDown, ChevronRight, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { useEvalRun, useEvalResults } from '@/lib/api/hooks'
import {
  Card, CardHeader, CardTitle, CardContent, Badge, Spinner,
  Table, Thead, Tbody, Th, Td, PageHeader,
} from '@/components/ui'
import { formatDate, formatScore, formatCost, formatLatency, statusColor, scoreColor, cn } from '@/lib/utils'
import type { EvalResult } from '@/lib/api/types'

function JudgeReasoningPanel({ judgeScores }: {
  judgeScores: Record<string, { score: number; passed: boolean; reasoning: string; flags: string[] }>
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {Object.entries(judgeScores).map(([slug, data]) => (
        <div key={slug} className={cn('rounded-lg border p-3 bg-white', data.passed ? 'border-green-200' : 'border-red-200')}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              {data.passed
                ? <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                : <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />}
              <span className="text-sm font-medium capitalize text-gray-800">
                {slug.replace(/_/g, ' ')}
              </span>
            </div>
            <span className={cn('text-sm font-bold', scoreColor(data.score))}>
              {formatScore(data.score)}
            </span>
          </div>
          {data.reasoning && (
            <p className="text-xs text-gray-600 leading-relaxed">{data.reasoning}</p>
          )}
          {data.flags && data.flags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {data.flags.map(f => (
                <span key={f} className="text-xs bg-red-50 text-red-700 px-1.5 py-0.5 rounded border border-red-100">{f}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function ResultRow({ result, judgeSlugs, index }: { result: EvalResult; judgeSlugs: string[]; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const hasError = Boolean(result.error_message)
  const hasSafetyFlags = result.safety_flags?.length > 0

  return (
    <>
      <tr
        className={cn('cursor-pointer transition-colors', expanded ? 'bg-blue-50' : 'hover:bg-gray-50', hasSafetyFlags && 'bg-red-50 hover:bg-red-100')}
        onClick={() => setExpanded(!expanded)}
      >
        <Td>
          <div className="flex items-center gap-2">
            {expanded ? <ChevronDown className="h-3.5 w-3.5 text-gray-400" /> : <ChevronRight className="h-3.5 w-3.5 text-gray-400" />}
            <span className="text-xs text-gray-500 font-mono">#{index + 1}</span>
            {hasSafetyFlags && <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
          </div>
        </Td>
        <Td>
          {hasError ? <Badge variant="warning">Error</Badge>
            : result.passed != null ? <Badge variant={result.passed ? 'success' : 'danger'}>{result.passed ? 'Pass' : 'Fail'}</Badge>
            : '—'}
        </Td>
        {judgeSlugs.map(slug => {
          const js = result.judge_scores?.[slug]
          return (
            <Td key={slug}>
              {js ? (
                <div className="flex items-center gap-1.5">
                  <div className="h-1.5 w-10 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className={cn('h-full rounded-full', js.score >= 0.8 ? 'bg-green-400' : js.score >= 0.6 ? 'bg-yellow-400' : 'bg-red-400')}
                      style={{ width: `${js.score * 100}%` }}
                    />
                  </div>
                  <span className={cn('text-xs font-medium', scoreColor(js.score))}>{formatScore(js.score)}</span>
                </div>
              ) : '—'}
            </Td>
          )
        })}
        <Td className="text-gray-500 text-xs">{formatLatency(result.latency_ms)}</Td>
        <Td className="text-gray-500 text-xs">{formatCost(result.cost_usd)}</Td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={4 + judgeSlugs.length} className="p-0">
            <div className="border-t border-b bg-gray-50 p-4 space-y-4">
              {result.agent_response && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Agent Response</p>
                  <p className="text-sm text-gray-800 leading-relaxed bg-white rounded-lg border p-3 whitespace-pre-wrap">{result.agent_response}</p>
                </div>
              )}
              {result.error_message && (
                <div>
                  <p className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">Error</p>
                  <p className="text-sm text-red-700 bg-red-50 rounded-lg border border-red-200 p-3">{result.error_message}</p>
                </div>
              )}
              {hasSafetyFlags && (
                <div>
                  <p className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">Safety Flags</p>
                  <div className="flex gap-2 flex-wrap">
                    {result.safety_flags.map(f => (
                      <span key={f} className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded border border-red-200">{f}</span>
                    ))}
                  </div>
                </div>
              )}
              {result.judge_scores && Object.keys(result.judge_scores).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Judge Reasoning</p>
                  <JudgeReasoningPanel judgeScores={result.judge_scores} />
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export default function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: run, isLoading } = useEvalRun(id!)
  const { data: results } = useEvalResults(id!, 100)
  const [showFailed, setShowFailed] = useState(false)

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  if (!run) return <div className="text-center py-20 text-gray-500">Run not found</div>

  const judgeSlugs = results?.items?.[0]?.judge_scores ? Object.keys(results.items[0].judge_scores) : []
  const failedCount = results?.items?.filter(r => !r.passed).length ?? 0
  const displayedResults = showFailed ? results?.items?.filter(r => !r.passed) : results?.items

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/runs')} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <PageHeader title={`Run ${run.id.slice(0, 8)}…`} description={`Triggered ${formatDate(run.created_at)}`} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Status', value: <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', statusColor(run.status))}>{run.status}</span> },
          { label: 'Pass Rate', value: run.pass_rate != null ? (
            <div>
              <p className={cn('text-2xl font-bold', run.pass_rate >= 0.8 ? 'text-green-700' : run.pass_rate >= 0.6 ? 'text-yellow-700' : 'text-red-700')}>
                {formatScore(run.pass_rate)}
              </p>
              <div className="w-full bg-gray-100 rounded-full h-1 mt-1">
                <div className={cn('h-1 rounded-full', run.pass_rate >= 0.8 ? 'bg-green-500' : run.pass_rate >= 0.6 ? 'bg-yellow-500' : 'bg-red-500')} style={{ width: `${run.pass_rate * 100}%` }} />
              </div>
            </div>
          ) : '—' },
          { label: 'Examples', value: <div><p className="text-2xl font-bold">{run.total_examples ?? '—'}</p>{failedCount > 0 && <p className="text-xs text-red-600">{failedCount} failed</p>}</div> },
          { label: 'Cost', value: <p className="text-lg font-semibold">{formatCost(run.total_cost_usd)}</p> },
          { label: 'Duration', value: <p className="text-lg font-semibold">{run.started_at && run.completed_at ? formatLatency(new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) : '—'}</p> },
        ].map(({ label, value }) => (
          <Card key={label}><CardContent className="py-3"><p className="text-xs text-gray-500 mb-1">{label}</p>{value}</CardContent></Card>
        ))}
      </div>

      {run.aggregate_scores && Object.keys(run.aggregate_scores).length > 0 && (
        <Card>
          <CardHeader><CardTitle>Aggregate Judge Scores</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {Object.entries(run.aggregate_scores).map(([slug, score]) => (
                <div key={slug} className="text-center">
                  <p className="text-xs text-gray-500 capitalize mb-1">{slug.replace(/_/g, ' ')}</p>
                  <p className={cn('text-2xl font-bold', scoreColor(score as number))}>{formatScore(score as number)}</p>
                  <div className="w-full bg-gray-100 rounded-full h-1 mt-1">
                    <div className={cn('h-1 rounded-full', (score as number) >= 0.8 ? 'bg-green-500' : (score as number) >= 0.6 ? 'bg-yellow-500' : 'bg-red-500')} style={{ width: `${(score as number) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {results?.items && results.items.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Results ({results.total} examples)</CardTitle>
              {failedCount > 0 && (
                <button
                  onClick={() => setShowFailed(!showFailed)}
                  className={cn('text-xs px-3 py-1.5 rounded-full border font-medium transition-colors',
                    showFailed ? 'bg-red-100 border-red-300 text-red-700' : 'bg-white border-gray-200 text-gray-500 hover:border-red-200 hover:text-red-600'
                  )}
                >
                  {showFailed ? `Show all (${results.total})` : `Show failed only (${failedCount})`}
                </button>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-1">Click any row to see agent response and judge reasoning</p>
          </CardHeader>
          <Table>
            <Thead>
              <tr>
                <Th className="w-16">#</Th>
                <Th className="w-20">Overall</Th>
                {judgeSlugs.map(s => <Th key={s} className="capitalize">{s.replace(/_/g, ' ')}</Th>)}
                <Th>Latency</Th>
                <Th>Cost</Th>
              </tr>
            </Thead>
            <Tbody>
              {displayedResults?.map((result, i) => (
                <ResultRow key={result.id} result={result} judgeSlugs={judgeSlugs} index={i} />
              ))}
            </Tbody>
          </Table>
        </Card>
      )}

      {run.error_message && (
        <Card>
          <CardHeader><CardTitle className="text-red-700">Run Error</CardTitle></CardHeader>
          <CardContent><pre className="text-sm text-red-600 whitespace-pre-wrap">{run.error_message}</pre></CardContent>
        </Card>
      )}
    </div>
  )
}
