import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Shield, Star } from 'lucide-react'
import { useTrace, useCreateAnnotation, usePromoteToGolden, useDatasets } from '@/lib/api/hooks'
import {
  Button, Card, CardHeader, CardTitle, CardContent,
  Badge, Spinner, Dialog, Textarea, Select, PageHeader,
} from '@/components/ui'
import { formatDate, priorityColor, cn } from '@/lib/utils'

export default function TraceDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: trace, isLoading } = useTrace(id!)
  const createAnnotation = useCreateAnnotation(id!)

  // Annotation state
  const [quality, setQuality] = useState<number | null>(null)
  const [safetyAssessment, setSafetyAssessment] = useState('')
  const [notes, setNotes] = useState('')
  const [saved, setSaved] = useState(false)
  const [annotationId, setAnnotationId] = useState<string | null>(null)

  // Promote to golden state
  const [promoteOpen, setPromoteOpen] = useState(false)
  const [promoteForm, setPromoteForm] = useState({
    dataset_id: '', query: '', expected_behaviors: '', prohibited_behaviors: '',
    persona: '', difficulty: 'medium', safety_tags: '', notes: '',
  })

  const { data: datasets } = useDatasets(trace?.agent_version_id || '')
  const promote = usePromoteToGolden(id!, annotationId || '')

  // Keyboard shortcuts: 1-5 to score, S to save, P to promote
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
    const num = parseInt(e.key)
    if (num >= 1 && num <= 5) setQuality(num)
    if (e.key === 's' || e.key === 'S') handleSave()
    if ((e.key === 'p' || e.key === 'P') && annotationId) setPromoteOpen(true)
  }, [annotationId])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const handleSave = async () => {
    if (!quality) return
    const result = await createAnnotation.mutateAsync({
      overall_quality: quality,
      safety_assessment: safetyAssessment || undefined,
      notes: notes || undefined,
    } as any)
    setAnnotationId((result as any).id)
    setSaved(true)
  }

  const handlePromote = async () => {
    await promote.mutateAsync({
      dataset_id: promoteForm.dataset_id,
      query: promoteForm.query || trace?.redacted_prompt || '',
      expected_behaviors: promoteForm.expected_behaviors.split('\n').filter(Boolean),
      prohibited_behaviors: promoteForm.prohibited_behaviors.split('\n').filter(Boolean),
      persona: promoteForm.persona || undefined,
      difficulty: promoteForm.difficulty,
      safety_tags: promoteForm.safety_tags.split(',').map(s => s.trim()).filter(Boolean),
      notes: promoteForm.notes || undefined,
    })
    setPromoteOpen(false)
  }

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  if (!trace) return <div className="text-center py-20 text-gray-500">Trace not found</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <PageHeader
          title={`Trace ${id!.slice(0, 8)}…`}
          description={`Captured ${formatDate(trace.created_at)}`}
        />
      </div>

      {/* Safety flags */}
      {trace.safety_flags.length > 0 && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
          <Shield className="h-4 w-4 text-red-500" />
          <div className="flex gap-2 flex-wrap">
            {trace.safety_flags.map(f => (
              <span key={f} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded border border-red-200">{f}</span>
            ))}
          </div>
          {trace.review_priority && (
            <span className={cn('ml-auto px-2 py-0.5 rounded-full text-xs font-medium border', priorityColor(trace.review_priority))}>
              {trace.review_priority}
            </span>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Prompt + Response */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Student Query</CardTitle>
              <div className="flex gap-2 mt-1">
                <Badge variant={trace.ferpa_classification === 'confidential' ? 'danger' : trace.ferpa_classification === 'directory' ? 'warning' : 'default'}>
                  FERPA: {trace.ferpa_classification}
                </Badge>
                {trace.model_id && <Badge variant="info">{trace.model_id}</Badge>}
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                {trace.redacted_prompt || <span className="text-gray-400 italic">No prompt stored</span>}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Agent Response</CardTitle></CardHeader>
            <CardContent>
              <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                {trace.redacted_response || <span className="text-gray-400 italic">No response stored</span>}
              </p>
            </CardContent>
          </Card>

          {trace.tool_calls && trace.tool_calls.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Tool Calls</CardTitle></CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-50 rounded p-3 overflow-x-auto">
                  {JSON.stringify(trace.tool_calls, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Annotation panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Annotation</CardTitle>
              <p className="text-xs text-gray-400 mt-1">Shortcuts: 1-5 to score · S to save · P to promote</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Quality score */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Overall Quality</label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map(n => (
                    <button
                      key={n}
                      onClick={() => setQuality(n)}
                      className={cn(
                        'h-9 w-9 rounded-full text-sm font-semibold transition-colors',
                        quality === n
                          ? 'bg-beacon-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
                      )}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>

              <Select
                label="Safety Assessment"
                value={safetyAssessment}
                onChange={e => setSafetyAssessment(e.target.value)}
                options={[
                  { value: '', label: 'Select…' },
                  { value: 'none', label: 'None — no safety concerns' },
                  { value: 'concerning', label: 'Concerning — warrants review' },
                  { value: 'crisis', label: 'Crisis — immediate action needed' },
                ]}
              />

              <Textarea
                label="Notes"
                rows={4}
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Optional notes about this trace…"
              />

              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  onClick={handleSave}
                  loading={createAnnotation.isPending}
                  disabled={!quality}
                >
                  {saved ? '✓ Saved' : 'Save (S)'}
                </Button>
                {saved && annotationId && (
                  <Button variant="outline" onClick={() => setPromoteOpen(true)}>
                    <Star className="h-4 w-4" />
                    Promote (P)
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Metadata */}
          <Card>
            <CardHeader><CardTitle>Metadata</CardTitle></CardHeader>
            <CardContent>
              <dl className="space-y-2 text-sm">
                {[
                  ['Input tokens', trace.input_tokens ?? '—'],
                  ['Output tokens', trace.output_tokens ?? '—'],
                  ['Latency', trace.latency_ms ? `${trace.latency_ms}ms` : '—'],
                  ['Session hash', trace.session_hash ? trace.session_hash.slice(0, 12) + '…' : '—'],
                  ['Langfuse ID', trace.langfuse_trace_id ? trace.langfuse_trace_id.slice(0, 12) + '…' : '—'],
                ].map(([k, v]) => (
                  <div key={String(k)} className="flex justify-between">
                    <dt className="text-gray-500">{k}</dt>
                    <dd className="font-mono text-xs text-gray-700">{String(v)}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Promote to golden dialog */}
      <Dialog open={promoteOpen} onClose={() => setPromoteOpen(false)} title="Promote to Golden Set" size="lg">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            This will create a new Example in the chosen dataset from this trace.
          </p>
          <Select
            label="Target Dataset"
            value={promoteForm.dataset_id}
            onChange={e => setPromoteForm(f => ({ ...f, dataset_id: e.target.value }))}
            options={[
              { value: '', label: 'Select dataset…' },
              ...(datasets?.items?.map(d => ({ value: d.id, label: `${d.name} (v${d.version})` })) ?? []),
            ]}
          />
          <Textarea
            label="Student Query"
            rows={2}
            value={promoteForm.query || trace.redacted_prompt || ''}
            onChange={e => setPromoteForm(f => ({ ...f, query: e.target.value }))}
          />
          <Textarea
            label="Expected Behaviors (one per line)"
            rows={3}
            value={promoteForm.expected_behaviors}
            onChange={e => setPromoteForm(f => ({ ...f, expected_behaviors: e.target.value }))}
            placeholder="Crisis signal acknowledged&#10;988 hotline provided&#10;Warm handoff offered"
          />
          <Textarea
            label="Prohibited Behaviors (one per line)"
            rows={2}
            value={promoteForm.prohibited_behaviors}
            onChange={e => setPromoteForm(f => ({ ...f, prohibited_behaviors: e.target.value }))}
            placeholder="Immediately processing drop request&#10;Dismissing student distress"
          />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Difficulty"
              value={promoteForm.difficulty}
              onChange={e => setPromoteForm(f => ({ ...f, difficulty: e.target.value }))}
              options={[
                { value: 'easy', label: 'Easy' },
                { value: 'medium', label: 'Medium' },
                { value: 'hard', label: 'Hard' },
                { value: 'adversarial', label: 'Adversarial' },
              ]}
            />
            <Select
              label="Persona"
              value={promoteForm.persona}
              onChange={e => setPromoteForm(f => ({ ...f, persona: e.target.value }))}
              options={[
                { value: '', label: 'Not specified' },
                { value: 'adult_learner', label: 'Adult Learner' },
                { value: 'first_gen', label: 'First Generation' },
                { value: 'military', label: 'Military' },
                { value: 'international', label: 'International' },
                { value: 'struggling', label: 'Struggling' },
                { value: 'traditional', label: 'Traditional' },
              ]}
            />
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setPromoteOpen(false)}>Cancel</Button>
            <Button onClick={handlePromote} loading={promote.isPending} disabled={!promoteForm.dataset_id}>
              <Star className="h-4 w-4" /> Promote to Golden Set
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
