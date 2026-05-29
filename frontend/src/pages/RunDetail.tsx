import { useParams } from 'react-router-dom'
import { useEvalRun, useEvalResults } from '@/lib/api/hooks'
import {
  Card, CardHeader, CardTitle, CardContent, Badge, Spinner,
  Table, Thead, Tbody, Th, Td, PageHeader,
} from '@/components/ui'
import { formatDate, formatScore, formatCost, formatLatency, statusColor, scoreColor, cn } from '@/lib/utils'

export default function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: run, isLoading } = useEvalRun(id!)
  const { data: results } = useEvalResults(id!)

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  if (!run) return <div className="text-center py-20 text-gray-500">Run not found</div>

  const judgeSlugs = results?.items?.[0]?.judge_scores
    ? Object.keys(results.items[0].judge_scores)
    : []

  return (
    <div className="space-y-6">
      <PageHeader title={`Run ${run.id.slice(0, 8)}…`} description={`Started ${formatDate(run.created_at)}`} />

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Status', value: <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', statusColor(run.status))}>{run.status}</span> },
          { label: 'Pass Rate', value: <span className={run.pass_rate != null ? (run.pass_rate >= 0.8 ? 'text-green-700 font-bold text-xl' : 'text-red-700 font-bold text-xl') : ''}>{formatScore(run.pass_rate)}</span> },
          { label: 'Examples', value: <span className="font-bold text-xl">{run.total_examples ?? '—'}</span> },
          { label: 'Total Cost', value: <span className="font-medium">{formatCost(run.total_cost_usd)}</span> },
          { label: 'Completed', value: <span className="text-sm text-gray-600">{formatDate(run.completed_at)}</span> },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardContent className="py-3">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              {value}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Aggregate judge scores */}
      {run.aggregate_scores && Object.keys(run.aggregate_scores).length > 0 && (
        <Card>
          <CardHeader><CardTitle>Aggregate Judge Scores</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {Object.entries(run.aggregate_scores).map(([slug, score]) => (
                <div key={slug} className="text-center">
                  <p className="text-xs text-gray-500 capitalize mb-1">{slug.replace(/_/g, ' ')}</p>
                  <p className={cn('text-2xl font-bold', scoreColor(score))}>{formatScore(score)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Per-example results */}
      {results?.items && results.items.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Results ({results.total} examples)</CardTitle></CardHeader>
          <Table>
            <Thead>
              <tr>
                <Th>Example</Th>
                <Th>Overall</Th>
                {judgeSlugs.map(s => <Th key={s}>{s.replace(/_/g, ' ')}</Th>)}
                <Th>Latency</Th>
                <Th>Cost</Th>
              </tr>
            </Thead>
            <Tbody>
              {results.items.map((result) => (
                <tr key={result.id} className="hover:bg-gray-50">
                  <Td><code className="text-xs">{result.example_id.slice(0, 8)}…</code></Td>
                  <Td>
                    {result.passed != null ? (
                      <Badge variant={result.passed ? 'success' : 'danger'}>
                        {result.passed ? 'Pass' : 'Fail'}
                      </Badge>
                    ) : result.error_message ? (
                      <Badge variant="warning">Error</Badge>
                    ) : '—'}
                  </Td>
                  {judgeSlugs.map(slug => {
                    const js = result.judge_scores?.[slug]
                    return (
                      <Td key={slug}>
                        {js ? (
                          <span className={cn('font-medium text-sm', scoreColor(js.score))}>
                            {formatScore(js.score)}
                          </span>
                        ) : '—'}
                      </Td>
                    )
                  })}
                  <Td className="text-gray-500">{formatLatency(result.latency_ms)}</Td>
                  <Td className="text-gray-500">{formatCost(result.cost_usd)}</Td>
                </tr>
              ))}
            </Tbody>
          </Table>
        </Card>
      )}

      {run.error_message && (
        <Card>
          <CardHeader><CardTitle className="text-red-700">Error</CardTitle></CardHeader>
          <CardContent>
            <pre className="text-sm text-red-600 whitespace-pre-wrap">{run.error_message}</pre>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
