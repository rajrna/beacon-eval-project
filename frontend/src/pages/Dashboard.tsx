import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  PlayCircle, Activity, AlertTriangle, DollarSign,
  Bot, Database, TrendingUp, Shield, ChevronRight,
} from 'lucide-react'
import { api } from '@/lib/api/client'
import { Card, CardHeader, CardTitle, CardContent, Spinner, Badge } from '@/components/ui'
import { formatScore, formatCost, formatDate, statusColor, scoreColor, cn } from '@/lib/utils'

interface DashboardMetrics {
  total_runs: number
  runs_this_week: number
  avg_pass_rate: number | null
  cost_this_week: number
  cost_all_time: number
  total_traces: number
  traces_this_week: number
  crisis_pending: number
  total_agents: number
  total_datasets: number
  total_examples: number
  recent_runs: {
    id: string
    status: string
    pass_rate: number | null
    total_examples: number | null
    total_cost_usd: number | null
    created_at: string | null
    aggregate_scores: Record<string, number> | null
    version_number: number | null
    agent_name: string | null
  }[]
}

function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardMetrics>('/v1/dashboard'),
    refetchInterval: 30_000,
  })
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  label, value, sub, icon: Icon, accent, onClick,
}: {
  label: string
  value: string | number
  sub?: string
  icon: React.ElementType
  accent?: 'green' | 'red' | 'yellow' | 'blue' | 'purple'
  onClick?: () => void
}) {
  const colors = {
    green: 'text-green-400 bg-green-900/20',
    red: 'text-red-400 bg-red-900/20',
    yellow: 'text-yellow-400 bg-yellow-900/20',
    blue: 'text-blue-400 bg-blue-900/20',
    purple: 'text-indigo-400 bg-indigo-900/20',
  }
  const color = colors[accent ?? 'blue']

  return (
    <Card
      className={cn('transition-colors', onClick && 'cursor-pointer hover:border-white/20')}
      onClick={onClick}
    >
      <CardContent className="py-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-2xl font-bold text-gray-100">{value}</p>
            {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
          </div>
          <div className={cn('h-9 w-9 rounded-lg flex items-center justify-center', color)}>
            <Icon className="h-4 w-4" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Pass rate bar ─────────────────────────────────────────────────────────────

function PassRateBar({ rate }: { rate: number }) {
  const color = rate >= 0.8 ? 'bg-green-500' : rate >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${rate * 100}%` }} />
      </div>
      <span className={cn('text-xs font-medium w-10 text-right', scoreColor(rate))}>
        {formatScore(rate)}
      </span>
    </div>
  )
}

// ── Judge score chips ─────────────────────────────────────────────────────────

function JudgeScoreChips({ scores }: { scores: Record<string, number> }) {
  return (
    <div className="flex gap-1 flex-wrap mt-1">
      {Object.entries(scores).map(([slug, score]) => (
        <span
          key={slug}
          className={cn(
            'text-xs px-1.5 py-0.5 rounded border',
            score >= 0.8
              ? 'bg-green-900/30 text-green-400 border-green-800'
              : score >= 0.6
              ? 'bg-yellow-900/30 text-yellow-400 border-yellow-800'
              : 'bg-red-900/30 text-red-400 border-red-800'
          )}
        >
          {slug.replace(/_/g, ' ').replace('mental health safety', 'mh safety')}: {formatScore(score)}
        </span>
      ))}
    </div>
  )
}

// ── Main dashboard ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()
  const { data, isLoading } = useDashboard()

  if (isLoading) return (
    <div className="flex items-center justify-center py-32">
      <Spinner size="lg" />
    </div>
  )

  if (!data) return null

  const hasRuns = data.total_runs > 0
  const hasCrisis = data.crisis_pending > 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Platform overview — updates every 30 seconds</p>
      </div>

      {/* Crisis alert */}
      {hasCrisis && (
        <div
          className="p-4 bg-red-900/20 border border-red-800 rounded-lg flex items-center gap-3 cursor-pointer hover:bg-red-900/30 transition-colors"
          onClick={() => navigate('/sme/queue')}
        >
          <AlertTriangle className="h-5 w-5 text-red-400 flex-shrink-0 animate-pulse" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-300">
              {data.crisis_pending} trace{data.crisis_pending !== 1 ? 's' : ''} pending review
            </p>
            <p className="text-xs text-red-500 mt-0.5">Click to open the SME review queue</p>
          </div>
          <ChevronRight className="h-4 w-4 text-red-500" />
        </div>
      )}

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Avg Pass Rate"
          value={data.avg_pass_rate != null ? formatScore(data.avg_pass_rate) : '—'}
          sub={`${data.total_runs} total runs`}
          icon={TrendingUp}
          accent={
            data.avg_pass_rate == null ? 'blue'
            : data.avg_pass_rate >= 0.8 ? 'green'
            : data.avg_pass_rate >= 0.6 ? 'yellow'
            : 'red'
          }
          onClick={() => navigate('/runs')}
        />
        <StatCard
          label="Runs This Week"
          value={data.runs_this_week}
          sub={`${data.total_runs} all time`}
          icon={PlayCircle}
          accent="purple"
          onClick={() => navigate('/runs')}
        />
        <StatCard
          label="Cost This Week"
          value={formatCost(data.cost_this_week)}
          sub={`${formatCost(data.cost_all_time)} all time`}
          icon={DollarSign}
          accent="blue"
        />
        <StatCard
          label="Pending Review"
          value={data.crisis_pending}
          sub={`${data.traces_this_week} traces this week`}
          icon={hasCrisis ? AlertTriangle : Shield}
          accent={hasCrisis ? 'red' : 'green'}
          onClick={() => navigate('/sme/queue')}
        />
      </div>

      {/* Secondary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Active Agents"
          value={data.total_agents}
          icon={Bot}
          accent="purple"
          onClick={() => navigate('/agents')}
        />
        <StatCard
          label="Datasets"
          value={data.total_datasets}
          sub={`${data.total_examples} examples`}
          icon={Database}
          accent="blue"
          onClick={() => navigate('/datasets')}
        />
        <StatCard
          label="Total Traces"
          value={data.total_traces}
          sub="production conversations"
          icon={Activity}
          accent="blue"
          onClick={() => navigate('/traces')}
        />
        <StatCard
          label="Traces This Week"
          value={data.traces_this_week}
          sub="from student chat"
          icon={Activity}
          accent="green"
          onClick={() => navigate('/traces')}
        />
      </div>

      {/* Recent runs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Eval Runs</CardTitle>
            <button
              onClick={() => navigate('/runs')}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              View all <ChevronRight className="h-3 w-3" />
            </button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {!hasRuns ? (
            <div className="px-6 py-12 text-center">
              <PlayCircle className="h-10 w-10 text-gray-700 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-400">No eval runs yet</p>
              <p className="text-xs text-gray-600 mt-1">Go to Eval Runs and trigger your first run</p>
              <button
                onClick={() => navigate('/runs')}
                className="mt-4 text-xs text-indigo-400 hover:text-indigo-300"
              >
                Go to Runs →
              </button>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {data.recent_runs.map(run => (
                <div
                  key={run.id}
                  className="px-4 py-3 flex items-start gap-4 cursor-pointer hover:bg-white/5 transition-colors"
                  onClick={() => navigate(`/runs/${run.id}`)}
                >
                  {/* Agent + status */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-200 truncate">
                        {run.agent_name ?? 'Unknown Agent'}
                      </span>
                      {run.version_number && (
                        <span className="text-xs text-gray-600 font-mono">v{run.version_number}</span>
                      )}
                      <span className={cn(
                        'text-xs px-1.5 py-0.5 rounded-full',
                        statusColor(run.status)
                      )}>
                        {run.status}
                      </span>
                    </div>

                    {/* Pass rate bar */}
                    {run.pass_rate != null && (
                      <PassRateBar rate={run.pass_rate} />
                    )}

                    {/* Judge scores */}
                    {run.aggregate_scores && Object.keys(run.aggregate_scores).length > 0 && (
                      <JudgeScoreChips scores={run.aggregate_scores} />
                    )}
                  </div>

                  {/* Meta */}
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-gray-500">
                      {run.total_examples ?? '?'} examples
                    </p>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {formatCost(run.total_cost_usd)}
                    </p>
                    <p className="text-xs text-gray-700 mt-0.5">
                      {run.created_at ? formatDate(run.created_at) : '—'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Trigger Eval Run', desc: 'Run agents against datasets', path: '/runs', icon: PlayCircle },
          { label: 'Student Chat', desc: 'Test agents in real-time', path: '/chat', icon: Bot },
          { label: 'SME Queue', desc: 'Review flagged traces', path: '/sme/queue', icon: Shield },
          { label: 'Browse Traces', desc: 'Inspect production data', path: '/traces', icon: Activity },
        ].map(({ label, desc, path, icon: Icon }) => (
          <button
            key={path}
            onClick={() => navigate(path)}
            className="p-4 rounded-lg border border-white/10 bg-white/3 hover:bg-white/5 hover:border-white/20 transition-all text-left group"
          >
            <Icon className="h-5 w-5 text-indigo-400 mb-2 group-hover:scale-110 transition-transform" />
            <p className="text-sm font-medium text-gray-200">{label}</p>
            <p className="text-xs text-gray-600 mt-0.5">{desc}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
