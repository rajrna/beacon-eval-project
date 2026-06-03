import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Trophy, Minus, TrendingUp, TrendingDown } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useAgent, useAgentVersions } from '@/lib/api/hooks'
import { api } from '@/lib/api/client'
import {
  Button, Card, CardHeader, CardTitle, CardContent,
  Spinner, PageHeader,
} from '@/components/ui'
import { formatScore, formatCost, formatLatency, scoreColor, cn } from '@/lib/utils'

interface JudgeComparison {
  judge_slug: string
  score_a: number | null
  score_b: number | null
  delta: number | null
  winner: 'a' | 'b' | 'tie' | null
}

interface ComparisonResult {
  agent_id: string
  agent_name: string
  version_a_id: string
  version_a_number: number
  version_a_run_id: string | null
  version_a_pass_rate: number | null
  version_a_cost: number | null
  version_a_latency_ms: number | null
  version_a_total_examples: number | null
  version_b_id: string
  version_b_number: number
  version_b_run_id: string | null
  version_b_pass_rate: number | null
  version_b_cost: number | null
  version_b_latency_ms: number | null
  version_b_total_examples: number | null
  dataset_id: string
  dataset_name: string
  pass_rate_delta: number | null
  overall_winner: 'a' | 'b' | 'tie' | null
  judge_comparisons: JudgeComparison[]
  examples_a_better: number
  examples_b_better: number
  examples_tied: number
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta == null) return <span className="text-gray-600 text-xs">—</span>
  const abs = Math.abs(delta)
  const pct = (abs * 100).toFixed(1)
  if (abs < 0.02) return (
    <span className="text-xs text-gray-500 flex items-center gap-0.5">
      <Minus className="h-3 w-3" /> tie
    </span>
  )
  if (delta > 0) return (
    <span className="text-xs text-green-400 flex items-center gap-0.5">
      <TrendingUp className="h-3 w-3" /> +{pct}%
    </span>
  )
  return (
    <span className="text-xs text-red-400 flex items-center gap-0.5">
      <TrendingDown className="h-3 w-3" /> -{pct}%
    </span>
  )
}

function ScoreCell({ score, isWinner }: { score: number | null; isWinner: boolean }) {
  if (score == null) return <td className="px-4 py-3 text-gray-600 text-sm text-center">—</td>
  return (
    <td className={cn(
      'px-4 py-3 text-center',
      isWinner && 'bg-green-900/20',
    )}>
      <div className="flex flex-col items-center gap-1">
        <span className={cn('text-sm font-bold', scoreColor(score))}>
          {formatScore(score)}
        </span>
        <div className="w-12 bg-white/5 rounded-full h-1">
          <div
            className={cn('h-1 rounded-full',
              score >= 0.8 ? 'bg-green-500' : score >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
            )}
            style={{ width: `${score * 100}%` }}
          />
        </div>
        {isWinner && <Trophy className="h-3 w-3 text-yellow-400" />}
      </div>
    </td>
  )
}

function WinnerBanner({ winner, nameA, nameB }: {
  winner: 'a' | 'b' | 'tie' | null
  nameA: string
  nameB: string
}) {
  if (!winner) return null

  if (winner === 'tie') return (
    <div className="p-4 bg-gray-800/50 border border-white/10 rounded-lg text-center">
      <Minus className="h-6 w-6 text-gray-400 mx-auto mb-1" />
      <p className="text-sm font-semibold text-gray-300">Too close to call</p>
      <p className="text-xs text-gray-500 mt-0.5">Pass rates within 2% — effectively equal</p>
    </div>
  )

  const winnerName = winner === 'a' ? nameA : nameB
  const loserName = winner === 'a' ? nameB : nameA

  return (
    <div className={cn(
      'p-4 rounded-lg border text-center',
      winner === 'b'
        ? 'bg-green-900/20 border-green-800'
        : 'bg-blue-900/20 border-blue-800'
    )}>
      <Trophy className={cn('h-6 w-6 mx-auto mb-1', winner === 'b' ? 'text-green-400' : 'text-blue-400')} />
      <p className="text-sm font-semibold text-gray-200">
        <span className={winner === 'b' ? 'text-green-400' : 'text-blue-400'}>{winnerName}</span> wins
      </p>
      <p className="text-xs text-gray-500 mt-0.5">Higher pass rate than {loserName}</p>
    </div>
  )
}

export default function AgentComparison() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [versionA, setVersionA] = useState('')
  const [versionB, setVersionB] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const { data: agent } = useAgent(id!)
  const { data: versions } = useAgentVersions(id!)

  const { data: result, isLoading, error } = useQuery({
    queryKey: ['comparison', id, versionA, versionB, datasetId],
    queryFn: () => {
      const params = new URLSearchParams({ version_a: versionA, version_b: versionB })
      if (datasetId) params.set('dataset_id', datasetId)
      return api.get<ComparisonResult>(`/v1/agents/${id}/compare?${params}`)
    },
    enabled: submitted && Boolean(versionA && versionB && versionA !== versionB),
    retry: false,
  })

  const versionList = versions?.items ?? []
  const nameA = versionA ? `v${versionList.find(v => v.id === versionA)?.version_number ?? '?'}` : 'Version A'
  const nameB = versionB ? `v${versionList.find(v => v.id === versionB)?.version_number ?? '?'}` : 'Version B'

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(`/agents/${id}`)} className="text-gray-500 hover:text-gray-300">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <PageHeader
          title={`Compare — ${agent?.name ?? '…'}`}
          description="Side-by-side eval results for two agent versions"
        />
      </div>

      {/* Version selector */}
      <Card>
        <CardHeader><CardTitle>Select Versions to Compare</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Version A</label>
              <select
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300"
                value={versionA}
                onChange={e => { setVersionA(e.target.value); setSubmitted(false) }}
              >
                <option value="">Select version…</option>
                {versionList.map(v => (
                  <option key={v.id} value={v.id} disabled={v.id === versionB}>
                    v{v.version_number} — {v.model_id}{v.is_locked ? ' (locked)' : ''}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Version B</label>
              <select
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300"
                value={versionB}
                onChange={e => { setVersionB(e.target.value); setSubmitted(false) }}
              >
                <option value="">Select version…</option>
                {versionList.map(v => (
                  <option key={v.id} value={v.id} disabled={v.id === versionA}>
                    v{v.version_number} — {v.model_id}{v.is_locked ? ' (locked)' : ''}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Dataset <span className="text-gray-600">(optional — auto-detects shared)</span>
              </label>
              <input
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300 placeholder-gray-600"
                placeholder="Dataset UUID (leave blank for auto)"
                value={datasetId}
                onChange={e => { setDatasetId(e.target.value); setSubmitted(false) }}
              />
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button
              onClick={() => setSubmitted(true)}
              disabled={!versionA || !versionB || versionA === versionB}
            >
              Compare
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Spinner size="lg" />
        </div>
      )}

      {/* Error */}
      {error && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-red-400 text-sm">
              {(error as any)?.message ?? 'Comparison failed. Make sure both versions have eval runs against the same dataset.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Winner banner */}
          <WinnerBanner winner={result.overall_winner} nameA={nameA} nameB={nameB} />

          {/* Top metrics comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Version A card */}
            <Card className={cn(result.overall_winner === 'a' && 'border-blue-700')}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    {nameA}
                    {result.overall_winner === 'a' && <Trophy className="h-4 w-4 text-yellow-400" />}
                  </CardTitle>
                  {result.version_a_run_id && (
                    <button
                      onClick={() => navigate(`/runs/${result.version_a_run_id}`)}
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      View run →
                    </button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Pass Rate</p>
                    {result.version_a_pass_rate != null ? (
                      <>
                        <p className={cn('text-3xl font-bold', scoreColor(result.version_a_pass_rate))}>
                          {formatScore(result.version_a_pass_rate)}
                        </p>
                        <div className="w-full bg-white/5 rounded-full h-1.5 mt-1">
                          <div
                            className={cn('h-1.5 rounded-full',
                              result.version_a_pass_rate >= 0.8 ? 'bg-green-500' :
                              result.version_a_pass_rate >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                            )}
                            style={{ width: `${result.version_a_pass_rate * 100}%` }}
                          />
                        </div>
                      </>
                    ) : <p className="text-gray-600 text-sm">No run data</p>}
                  </div>
                  <div className="grid grid-cols-3 gap-3 pt-2 border-t border-white/5 text-xs">
                    <div>
                      <p className="text-gray-500">Examples</p>
                      <p className="text-gray-200 font-medium">{result.version_a_total_examples ?? '—'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Cost</p>
                      <p className="text-gray-200 font-medium">{formatCost(result.version_a_cost)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Latency</p>
                      <p className="text-gray-200 font-medium">{formatLatency(result.version_a_latency_ms)}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Version B card */}
            <Card className={cn(result.overall_winner === 'b' && 'border-green-700')}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    {nameB}
                    {result.overall_winner === 'b' && <Trophy className="h-4 w-4 text-yellow-400" />}
                  </CardTitle>
                  {result.version_b_run_id && (
                    <button
                      onClick={() => navigate(`/runs/${result.version_b_run_id}`)}
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      View run →
                    </button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Pass Rate</p>
                    {result.version_b_pass_rate != null ? (
                      <>
                        <p className={cn('text-3xl font-bold', scoreColor(result.version_b_pass_rate))}>
                          {formatScore(result.version_b_pass_rate)}
                        </p>
                        <div className="w-full bg-white/5 rounded-full h-1.5 mt-1">
                          <div
                            className={cn('h-1.5 rounded-full',
                              result.version_b_pass_rate >= 0.8 ? 'bg-green-500' :
                              result.version_b_pass_rate >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                            )}
                            style={{ width: `${result.version_b_pass_rate * 100}%` }}
                          />
                        </div>
                      </>
                    ) : <p className="text-gray-600 text-sm">No run data</p>}
                  </div>
                  <div className="grid grid-cols-3 gap-3 pt-2 border-t border-white/5 text-xs">
                    <div>
                      <p className="text-gray-500">Examples</p>
                      <p className="text-gray-200 font-medium">{result.version_b_total_examples ?? '—'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Cost</p>
                      <p className="text-gray-200 font-medium">{formatCost(result.version_b_cost)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Latency</p>
                      <p className="text-gray-200 font-medium">{formatLatency(result.version_b_latency_ms)}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Judge scores table */}
          {result.judge_comparisons.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Judge Score Breakdown</CardTitle>
                  <p className="text-xs text-gray-500">Dataset: {result.dataset_name}</p>
                </div>
              </CardHeader>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Judge</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">{nameA}</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">{nameB}</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Delta</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {result.judge_comparisons.map(jc => (
                      <tr key={jc.judge_slug} className="hover:bg-white/3">
                        <td className="px-4 py-3">
                          <span className="text-sm capitalize text-gray-300">
                            {jc.judge_slug.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <ScoreCell score={jc.score_a} isWinner={jc.winner === 'a'} />
                        <ScoreCell score={jc.score_b} isWinner={jc.winner === 'b'} />
                        <td className="px-4 py-3 text-center">
                          <DeltaBadge delta={jc.delta} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Example breakdown */}
          <Card>
            <CardHeader><CardTitle>Example-Level Breakdown</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className={cn('p-4 rounded-lg', result.examples_a_better > result.examples_b_better ? 'bg-blue-900/20 border border-blue-800' : 'bg-white/3 border border-white/5')}>
                  <p className="text-2xl font-bold text-blue-400">{result.examples_a_better}</p>
                  <p className="text-xs text-gray-500 mt-1">{nameA} better</p>
                </div>
                <div className="p-4 rounded-lg bg-white/3 border border-white/5">
                  <p className="text-2xl font-bold text-gray-400">{result.examples_tied}</p>
                  <p className="text-xs text-gray-500 mt-1">Tied</p>
                </div>
                <div className={cn('p-4 rounded-lg', result.examples_b_better > result.examples_a_better ? 'bg-green-900/20 border border-green-800' : 'bg-white/3 border border-white/5')}>
                  <p className="text-2xl font-bold text-green-400">{result.examples_b_better}</p>
                  <p className="text-xs text-gray-500 mt-1">{nameB} better</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
