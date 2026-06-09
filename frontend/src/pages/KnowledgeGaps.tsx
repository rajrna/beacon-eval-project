import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, TrendingUp, AlertCircle, BookOpen, Clock, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api/client'
import { Card, CardHeader, CardTitle, CardContent, Spinner } from '@/components/ui'
import { useInstitutions, usePrograms } from '@/lib/api/hooks'
import { formatDate, cn } from '@/lib/utils'

interface KnowledgeGap {
  query: string
  occurrence_count: number
  first_seen: string | null
  last_seen: string | null
}

function useKnowledgeGaps(programId: string | null) {
  return useQuery({
    queryKey: ['knowledge-gaps', programId],
    queryFn: () => api.get<KnowledgeGap[]>(`/v1/programs/${programId}/knowledge/gaps?limit=50`),
    enabled: Boolean(programId),
  })
}

function FrequencyBar({ count, max }: { count: number; max: number }) {
  const pct = max > 0 ? (count / max) * 100 : 0
  const color = count >= 10 ? 'bg-red-500' : count >= 5 ? 'bg-yellow-500' : 'bg-indigo-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn(
        'text-xs font-mono w-6 text-right',
        count >= 10 ? 'text-red-400' : count >= 5 ? 'text-yellow-400' : 'text-indigo-400'
      )}>
        {count}
      </span>
    </div>
  )
}

function GapRow({ gap, max }: { gap: KnowledgeGap; max: number }) {
  const urgency = gap.occurrence_count >= 10 ? 'high' : gap.occurrence_count >= 5 ? 'medium' : 'low'

  return (
    <div className="px-4 py-3 hover:bg-white/3 transition-colors group">
      <div className="flex items-start gap-3">
        {/* Urgency indicator */}
        <div className={cn(
          'mt-1 h-2 w-2 rounded-full flex-shrink-0',
          urgency === 'high' ? 'bg-red-500' :
          urgency === 'medium' ? 'bg-yellow-500' : 'bg-indigo-500/50'
        )} />

        <div className="flex-1 min-w-0">
          {/* Query text */}
          <p className="text-sm text-gray-200 leading-relaxed">
            "{gap.query}"
          </p>

          {/* Frequency bar */}
          <div className="mt-2 max-w-xs">
            <FrequencyBar count={gap.occurrence_count} max={max} />
          </div>

          {/* Meta */}
          <div className="flex items-center gap-3 mt-1.5">
            <span className="text-xs text-gray-600 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Last seen {gap.last_seen ? formatDate(gap.last_seen) : '—'}
            </span>
            {gap.first_seen && gap.last_seen && gap.first_seen !== gap.last_seen && (
              <span className="text-xs text-gray-700">
                First seen {formatDate(gap.first_seen)}
              </span>
            )}
          </div>
        </div>

        {/* Count badge */}
        <div className={cn(
          'flex-shrink-0 px-2 py-0.5 rounded text-xs font-mono font-medium',
          urgency === 'high' ? 'bg-red-900/30 text-red-400 border border-red-800' :
          urgency === 'medium' ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-800' :
          'bg-indigo-900/20 text-indigo-400 border border-indigo-900'
        )}>
          ×{gap.occurrence_count}
        </div>
      </div>
    </div>
  )
}

export default function KnowledgeGaps() {
  const [institutionId, setInstitutionId] = useState('')
  const [programId, setProgramId] = useState('')
  const [search, setSearch] = useState('')

  const { data: institutions } = useInstitutions()
  const { data: programs } = usePrograms(institutionId)
  const { data: gaps, isLoading, refetch, isFetching } = useKnowledgeGaps(programId || null)

  const filtered = (gaps || []).filter(g =>
    !search || g.query.toLowerCase().includes(search.toLowerCase())
  )

  const maxCount = Math.max(...(filtered.map(g => g.occurrence_count)), 1)
  const highPriority = filtered.filter(g => g.occurrence_count >= 10).length
  const mediumPriority = filtered.filter(g => g.occurrence_count >= 5 && g.occurrence_count < 10).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Knowledge Gaps</h1>
          <p className="text-sm text-gray-500 mt-1">
            Student questions that returned no knowledge base results — add these as facts to improve RAG accuracy
          </p>
        </div>
        {programId && (
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', isFetching && 'animate-spin')} />
            Refresh
          </button>
        )}
      </div>

      {/* Program selector */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-3">
            <select
              className="text-sm rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-gray-300"
              value={institutionId}
              onChange={e => { setInstitutionId(e.target.value); setProgramId('') }}
            >
              <option value="">Select institution…</option>
              {institutions?.items?.map(i => (
                <option key={i.id} value={i.id}>{i.name}</option>
              ))}
            </select>

            <select
              className="text-sm rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-gray-300"
              value={programId}
              onChange={e => setProgramId(e.target.value)}
              disabled={!institutionId}
            >
              <option value="">Select program…</option>
              {programs?.items?.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      {gaps && gaps.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-indigo-900/30 flex items-center justify-center">
                  <BookOpen className="h-4 w-4 text-indigo-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">Total gaps</p>
                  <p className="text-xl font-bold text-gray-100">{gaps.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-red-900/20 flex items-center justify-center">
                  <AlertCircle className="h-4 w-4 text-red-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">High priority (10+)</p>
                  <p className="text-xl font-bold text-gray-100">{highPriority}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-yellow-900/20 flex items-center justify-center">
                  <TrendingUp className="h-4 w-4 text-yellow-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">Medium priority (5–9)</p>
                  <p className="text-xl font-bold text-gray-100">{mediumPriority}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Gaps table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              {programId
                ? `Unanswered queries${filtered.length > 0 ? ` (${filtered.length})` : ''}`
                : 'Select a program to view gaps'}
            </CardTitle>

            {gaps && gaps.length > 0 && (
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search queries…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-xs rounded-md border border-white/10 bg-white/5 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-indigo-500 w-52"
                />
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {!programId ? (
            <div className="px-6 py-16 text-center">
              <BookOpen className="h-10 w-10 text-gray-700 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-400">No program selected</p>
              <p className="text-xs text-gray-600 mt-1">
                Select an institution and program above to view knowledge gaps
              </p>
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner size="lg" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <TrendingUp className="h-10 w-10 text-gray-700 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-400">
                {search ? 'No gaps match your search' : 'No knowledge gaps detected yet'}
              </p>
              <p className="text-xs text-gray-600 mt-1">
                {search
                  ? 'Try a different search term'
                  : 'Gaps appear when students ask questions the knowledge base cannot answer'}
              </p>
            </div>
          ) : (
            <>
              {/* Legend */}
              <div className="px-4 py-2 border-b border-white/5 flex items-center gap-4">
                <span className="text-xs text-gray-600 flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-red-500" /> High priority (10+ occurrences)
                </span>
                <span className="text-xs text-gray-600 flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-yellow-500" /> Medium (5–9)
                </span>
                <span className="text-xs text-gray-600 flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-indigo-500/50" /> Low (1–4)
                </span>
              </div>

              <div className="divide-y divide-white/5">
                {filtered.map((gap, i) => (
                  <GapRow key={i} gap={gap} max={maxCount} />
                ))}
              </div>

              <div className="px-4 py-3 border-t border-white/5">
                <p className="text-xs text-gray-600">
                  Add high-priority gaps as knowledge entries at{' '}
                  <span className="text-indigo-400">
                    /v1/programs/{programId}/knowledge
                  </span>{' '}
                  to improve RAG accuracy for these questions.
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
