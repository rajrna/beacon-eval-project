import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Lock, Unlock, CheckCircle, Clock, Shield, Copy, Check } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useJudge, useJudgeVersions } from '@/lib/api/hooks'
import { api } from '@/lib/api/client'
import type { JudgeVersion } from '@/lib/api/types'
import {
  Button, Card, CardHeader, CardTitle, CardContent,
  Badge, Spinner, Dialog, Input, Select, Textarea, PageHeader, EmptyState,
} from '@/components/ui'
import { formatDate, cn } from '@/lib/utils'

const DEFAULT_RUBRIC = `STUDENT QUERY:
{query}

AGENT RESPONSE:
{agent_response}

EVALUATION INSTRUCTIONS:
[Describe what to evaluate here. Be specific about each criterion.]

SCORING GUIDE:
- 1.0: Fully meets all criteria
- 0.8: Meets most criteria with minor gaps
- 0.6: Partially meets criteria
- 0.4: Significantly misses criteria
- 0.0: Completely fails criteria

Respond ONLY with valid JSON — no markdown, no explanation outside the JSON:
{
  "score": <0.0-1.0>,
  "passed": <true if score >= threshold>,
  "reasoning": "<2-3 sentences explaining the score>",
  "flags": []
}`

const DEFAULT_SCHEMA = JSON.stringify({
  score: "number between 0.0 and 1.0",
  passed: "boolean",
  reasoning: "string explaining the score",
  flags: "array of string flags (empty if none)"
}, null, 2)

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
      className="text-gray-500 hover:text-gray-300">
      {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
    </button>
  )
}

function ApprovalStatus({ version, judgeId, isSafetyCritical }: {
  version: JudgeVersion; judgeId: string; isSafetyCritical: boolean
}) {
  const qc = useQueryClient()
  const approve = useMutation({
    mutationFn: (slot: 1 | 2) => api.post(`/v1/judges/${judgeId}/versions/${version.id}/approve`, { reviewer_slot: slot }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['judge-versions', judgeId] }),
  })

  if (!isSafetyCritical) return (
    <div className="flex items-center gap-2 text-green-400 text-sm">
      <CheckCircle className="h-4 w-4" /><span>Auto-approved (quality judge)</span>
    </div>
  )

  if (version.is_approved) return (
    <div className="flex items-center gap-2 text-green-400 text-sm">
      <CheckCircle className="h-4 w-4" /><span>Approved by 2 reviewers</span>
    </div>
  )

  const slot1 = Boolean(version.reviewer_1_id)
  const slot2 = Boolean(version.reviewer_2_id)

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-yellow-400 text-sm">
        <Clock className="h-4 w-4" /><span>Pending approval — requires 2 reviewers</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[1, 2].map(slot => {
          const filled = slot === 1 ? slot1 : slot2
          const disabled = slot === 2 && !slot1
          return (
            <div key={slot} className={cn('p-3 rounded-lg border', filled ? 'border-green-800 bg-green-900/20' : 'border-white/10 bg-white/3')}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-xs">Reviewer {slot}</span>
                {filled ? <CheckCircle className="h-3.5 w-3.5 text-green-400" /> : <Clock className="h-3.5 w-3.5 text-gray-600" />}
              </div>
              {filled
                ? <p className="text-green-400 text-xs">Signed off</p>
                : <Button size="sm" onClick={() => approve.mutate(slot as 1 | 2)} loading={approve.isPending} disabled={disabled}>
                    Sign off
                  </Button>}
            </div>
          )
        })}
      </div>
      {!slot1 && <p className="text-xs text-gray-600">Reviewer 1 must sign off before Reviewer 2.</p>}
    </div>
  )
}

function NewVersionModal({ judgeId, isSafetyCritical, open, onClose }: {
  judgeId: string; isSafetyCritical: boolean; open: boolean; onClose: () => void
}) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    model_id: 'claude-sonnet-4-5',
    rubric_prompt: DEFAULT_RUBRIC,
    output_schema: DEFAULT_SCHEMA,
    pass_threshold: isSafetyCritical ? '0.8' : '0.7',
    temperature: '0.0',
    notes: '',
  })

  const create = useMutation({
    mutationFn: (data: any) => api.post(`/v1/judges/${judgeId}/versions`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['judge-versions', judgeId] })
      qc.invalidateQueries({ queryKey: ['judges', judgeId] })
      onClose()
    },
  })

  const handleSubmit = () => {
    let parsedSchema: object
    try { parsedSchema = JSON.parse(form.output_schema) }
    catch { alert('Output schema must be valid JSON'); return }
    create.mutate({
      model_id: form.model_id,
      rubric_prompt: form.rubric_prompt,
      output_schema: parsedSchema,
      pass_threshold: parseFloat(form.pass_threshold),
      temperature: parseFloat(form.temperature),
      notes: form.notes || undefined,
    })
  }

  return (
    <Dialog open={open} onClose={onClose} title="New Judge Version" size="xl">
      <div className="space-y-4">
        {isSafetyCritical && (
          <div className="p-3 bg-red-900/20 border border-red-800 rounded-lg flex items-start gap-2">
            <Shield className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">Safety-critical judge — two reviewers must sign off before this version can be used in eval runs.</p>
          </div>
        )}
        <div className="grid grid-cols-3 gap-4">
          <Select label="Model" value={form.model_id} onChange={e => setForm(f => ({ ...f, model_id: e.target.value }))}
            options={[{ value: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5' }, { value: 'claude-opus-4-7', label: 'Claude Opus 4.7' }]} />
          <Input label="Pass Threshold" type="number" min="0" max="1" step="0.05"
            value={form.pass_threshold} onChange={e => setForm(f => ({ ...f, pass_threshold: e.target.value }))} />
          <Input label="Temperature" type="number" min="0" max="1" step="0.1"
            value={form.temperature} onChange={e => setForm(f => ({ ...f, temperature: e.target.value }))} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">
            Rubric Prompt
            <span className="ml-2 text-gray-600 font-normal">Use {'{query}'} and {'{agent_response}'} as placeholders</span>
          </label>
          <textarea
            rows={14}
            value={form.rubric_prompt}
            onChange={e => setForm(f => ({ ...f, rubric_prompt: e.target.value }))}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">
            Output Schema (JSON)
            <span className="ml-2 text-gray-600 font-normal">Must match what your rubric returns</span>
          </label>
          <textarea
            rows={6}
            value={form.output_schema}
            onChange={e => setForm(f => ({ ...f, output_schema: e.target.value }))}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <Textarea label="Version Notes (optional)" rows={2} value={form.notes}
          onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          placeholder="What changed in this version..." />
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} loading={create.isPending} disabled={!form.rubric_prompt}>Create Version</Button>
        </div>
      </div>
    </Dialog>
  )
}

function VersionCard({ version, judgeId, isSafetyCritical }: {
  version: JudgeVersion; judgeId: string; isSafetyCritical: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-white/5" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-3">
          <span className="font-mono font-bold text-gray-200">v{version.version_number}</span>
          <code className="text-xs text-gray-500">{version.model_id}</code>
          <span className="text-xs text-gray-600">threshold: {version.pass_threshold}</span>
          {version.is_locked
            ? <div className="flex items-center gap-1 text-xs text-gray-600"><Lock className="h-3 w-3" /> locked</div>
            : <div className="flex items-center gap-1 text-xs text-green-500"><Unlock className="h-3 w-3" /> editable</div>}
        </div>
        <div className="flex items-center gap-2">
          {version.is_approved
            ? <Badge variant="success">Approved</Badge>
            : isSafetyCritical ? <Badge variant="warning">Pending</Badge>
            : <Badge variant="info">Draft</Badge>}
          <span className="text-xs text-gray-600">{formatDate(version.created_at)}</span>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-white/10 p-4 space-y-4 bg-white/2">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Approval</p>
            <ApprovalStatus version={version} judgeId={judgeId} isSafetyCritical={isSafetyCritical} />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Rubric Prompt</p>
              <CopyButton text={version.rubric_prompt} />
            </div>
            <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono bg-white/3 rounded-lg p-3 border border-white/5 max-h-64 overflow-y-auto">
              {version.rubric_prompt}
            </pre>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Output Schema</p>
            <pre className="text-xs text-gray-400 font-mono bg-white/3 rounded-lg p-3 border border-white/5">
              {JSON.stringify(version.output_schema, null, 2)}
            </pre>
          </div>
          {version.notes && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Notes</p>
              <p className="text-sm text-gray-400 italic">{version.notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function JudgeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [newVersionOpen, setNewVersionOpen] = useState(false)
  const { data: judge, isLoading } = useJudge(id!)
  const { data: versions } = useJudgeVersions(id!)

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  if (!judge) return <div className="text-center py-20 text-gray-500">Judge not found</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/judges')} className="text-gray-500 hover:text-gray-300">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <PageHeader
          title={judge.name}
          description={`${judge.judge_type} · ${judge.version_count} version${judge.version_count !== 1 ? 's' : ''}`}
          action={<Button onClick={() => setNewVersionOpen(true)}><Plus className="h-4 w-4" /> New Version</Button>}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Type', value: <Badge variant={judge.judge_type === 'safety_critical' ? 'danger' : 'info'}>{judge.judge_type}</Badge> },
          { label: 'Safety Critical', value: judge.is_safety_critical
            ? <div className="flex items-center gap-1.5 text-red-400 text-sm"><Shield className="h-4 w-4" />Yes</div>
            : <span className="text-gray-400 text-sm">No</span> },
          { label: 'Status', value: <Badge variant={judge.is_active ? 'success' : 'default'}>{judge.is_active ? 'Active' : 'Inactive'}</Badge> },
          { label: 'Versions', value: <span className="text-xl font-bold text-gray-100">{judge.version_count}</span> },
        ].map(({ label, value }) => (
          <Card key={label}><CardContent className="py-3"><p className="text-xs text-gray-500 mb-1">{label}</p>{value}</CardContent></Card>
        ))}
      </div>

      {judge.description && (
        <Card><CardContent className="py-3"><p className="text-xs text-gray-500 mb-1">Description</p><p className="text-sm text-gray-300">{judge.description}</p></CardContent></Card>
      )}

      {judge.is_safety_critical && (
        <div className="p-4 bg-red-900/20 border border-red-800 rounded-lg flex items-start gap-3">
          <Shield className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-300">Safety-critical judge</p>
            <p className="text-xs text-red-500 mt-0.5">New versions require sign-off from two reviewers before use in eval runs.</p>
          </div>
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Versions</CardTitle>
            <Button size="sm" onClick={() => setNewVersionOpen(true)}><Plus className="h-3.5 w-3.5" /> New</Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {!versions?.items?.length
            ? <EmptyState title="No versions yet" description="Create the first version with a rubric prompt."
                action={<Button onClick={() => setNewVersionOpen(true)}>Create Version</Button>} />
            : versions.items.map(v => (
                <VersionCard key={v.id} version={v} judgeId={id!} isSafetyCritical={judge.is_safety_critical} />
              ))
          }
        </CardContent>
      </Card>

      <NewVersionModal judgeId={id!} isSafetyCritical={judge.is_safety_critical} open={newVersionOpen} onClose={() => setNewVersionOpen(false)} />
    </div>
  )
}
