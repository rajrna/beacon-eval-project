import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Shield, ChevronDown, ChevronRight, Filter } from 'lucide-react'
import { useDataset, useExamples } from '@/lib/api/hooks'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import type { Example } from '@/lib/api/types'
import {
  Button, Card, CardHeader, CardTitle, CardContent,
  Badge, Spinner, Dialog, Input, Textarea, Select,
  Table, Thead, Tbody, Th, Td, PageHeader, EmptyState,
} from '@/components/ui'
import { formatDate, cn } from '@/lib/utils'

const PERSONAS = [
  { value: '', label: 'All personas' },
  { value: 'adult_learner', label: 'Adult Learner' },
  { value: 'first_gen', label: 'First Generation' },
  { value: 'military', label: 'Military' },
  { value: 'international', label: 'International' },
  { value: 'struggling', label: 'Struggling' },
  { value: 'traditional', label: 'Traditional' },
]

const DIFFICULTIES = [
  { value: '', label: 'All difficulties' },
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
  { value: 'adversarial', label: 'Adversarial' },
]

function difficultyColor(d: string) {
  switch (d) {
    case 'easy': return 'bg-green-900/30 text-green-400 border-green-800'
    case 'medium': return 'bg-blue-900/30 text-blue-400 border-blue-800'
    case 'hard': return 'bg-orange-900/30 text-orange-400 border-orange-800'
    case 'adversarial': return 'bg-red-900/30 text-red-400 border-red-800'
    default: return 'bg-gray-800 text-gray-400 border-gray-700'
  }
}

function ExampleRow({ example }: { example: Example }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <tr
        className="cursor-pointer hover:bg-white/5 transition-colors border-b border-white/5"
        onClick={() => setExpanded(!expanded)}
      >
        <Td>
          <div className="flex items-center gap-2">
            {expanded
              ? <ChevronDown className="h-3.5 w-3.5 text-gray-500" />
              : <ChevronRight className="h-3.5 w-3.5 text-gray-500" />
            }
            {example.is_safety_tagged && (
              <Shield className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
            )}
          </div>
        </Td>
        <Td>
          <p className="text-sm text-gray-200 line-clamp-2 max-w-md">{example.query}</p>
        </Td>
        <Td>
          {example.persona ? (
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-900/40 text-indigo-300 border border-indigo-800">
              {example.persona.replace(/_/g, ' ')}
            </span>
          ) : <span className="text-gray-600 text-xs">—</span>}
        </Td>
        <Td>
          <span className={cn('text-xs px-2 py-0.5 rounded-full border', difficultyColor(example.difficulty))}>
            {example.difficulty}
          </span>
        </Td>
        <Td>
          {example.safety_tags.length > 0 ? (
            <div className="flex gap-1 flex-wrap max-w-xs">
              {example.safety_tags.map(t => (
                <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-900">
                  {t}
                </span>
              ))}
            </div>
          ) : <span className="text-gray-600 text-xs">—</span>}
        </Td>
        <Td className="text-gray-500 text-xs">{formatDate(example.created_at)}</Td>
      </tr>

      {expanded && (
        <tr className="border-b border-white/5">
          <td colSpan={6} className="p-0">
            <div className="bg-white/3 px-6 py-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Expected Behaviors
                  </p>
                  <ul className="space-y-1">
                    {example.expected_behaviors.map((b, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                        <span className="text-green-500 mt-0.5 flex-shrink-0">✓</span>
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Prohibited Behaviors
                  </p>
                  <ul className="space-y-1">
                    {example.prohibited_behaviors.length > 0
                      ? example.prohibited_behaviors.map((b, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                            <span className="text-red-500 mt-0.5 flex-shrink-0">✗</span>
                            {b}
                          </li>
                        ))
                      : <li className="text-gray-600 text-sm">None specified</li>
                    }
                  </ul>
                </div>
              </div>
              {example.notes && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Notes</p>
                  <p className="text-sm text-gray-400 italic">{example.notes}</p>
                </div>
              )}
              {example.reference_answer && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Reference Answer</p>
                  <p className="text-sm text-gray-300 bg-white/5 rounded-lg p-3">{example.reference_answer}</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function AddExampleModal({ datasetId, open, onClose }: {
  datasetId: string
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    query: '',
    expected_behaviors: '',
    prohibited_behaviors: '',
    reference_answer: '',
    persona: '',
    difficulty: 'medium',
    safety_tags: '',
    notes: '',
  })

  const create = useMutation({
    mutationFn: (data: any) =>
      api.post(`/v1/datasets/${datasetId}/examples`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['examples', datasetId] })
      qc.invalidateQueries({ queryKey: ['datasets', datasetId] })
      onClose()
      setForm({
        query: '', expected_behaviors: '', prohibited_behaviors: '',
        reference_answer: '', persona: '', difficulty: 'medium',
        safety_tags: '', notes: '',
      })
    },
  })

  const handleSubmit = () => {
    const safety_tags = form.safety_tags.split(',').map(s => s.trim()).filter(Boolean)
    create.mutate({
      query: form.query,
      expected_behaviors: form.expected_behaviors.split('\n').filter(Boolean),
      prohibited_behaviors: form.prohibited_behaviors.split('\n').filter(Boolean),
      reference_answer: form.reference_answer || null,
      persona: form.persona || null,
      difficulty: form.difficulty,
      safety_tags,
      notes: form.notes || null,
    })
  }

  return (
    <Dialog open={open} onClose={onClose} title="Add Example" size="xl">
      <div className="space-y-4">
        <Textarea
          label="Student Query"
          rows={3}
          value={form.query}
          onChange={e => setForm(f => ({ ...f, query: e.target.value }))}
          placeholder="What are the admission requirements for the MBA program?"
        />
        <div className="grid grid-cols-2 gap-4">
          <Textarea
            label="Expected Behaviors (one per line)"
            rows={4}
            value={form.expected_behaviors}
            onChange={e => setForm(f => ({ ...f, expected_behaviors: e.target.value }))}
            placeholder={"State requirements clearly\nMention work experience\nOffer next steps"}
          />
          <Textarea
            label="Prohibited Behaviors (one per line)"
            rows={4}
            value={form.prohibited_behaviors}
            onChange={e => setForm(f => ({ ...f, prohibited_behaviors: e.target.value }))}
            placeholder={"Give incorrect requirements\nDiscourage the applicant"}
          />
        </div>
        <Textarea
          label="Reference Answer (optional)"
          rows={3}
          value={form.reference_answer}
          onChange={e => setForm(f => ({ ...f, reference_answer: e.target.value }))}
          placeholder="Ideal response text..."
        />
        <div className="grid grid-cols-3 gap-4">
          <Select
            label="Persona"
            value={form.persona}
            onChange={e => setForm(f => ({ ...f, persona: e.target.value }))}
            options={PERSONAS}
          />
          <Select
            label="Difficulty"
            value={form.difficulty}
            onChange={e => setForm(f => ({ ...f, difficulty: e.target.value }))}
            options={DIFFICULTIES.slice(1)}
          />
          <Input
            label="Safety Tags (comma separated)"
            value={form.safety_tags}
            onChange={e => setForm(f => ({ ...f, safety_tags: e.target.value }))}
            placeholder="mental_health, crisis_referral"
          />
        </div>
        <Textarea
          label="Notes (optional)"
          rows={2}
          value={form.notes}
          onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          placeholder="Notes for SME reviewers..."
        />
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            loading={create.isPending}
            disabled={!form.query || !form.expected_behaviors}
          >
            Add Example
          </Button>
        </div>
      </div>
    </Dialog>
  )
}

export default function DatasetDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [difficulty, setDifficulty] = useState('')
  const [persona, setPersona] = useState('')
  const [offset, setOffset] = useState(0)
  const [addOpen, setAddOpen] = useState(false)
  const LIMIT = 20

  const { data: dataset, isLoading: loadingDataset } = useDataset(id!)
  const { data: examples, isLoading: loadingExamples } = useExamples(id!, LIMIT, offset, difficulty, persona)

  if (loadingDataset) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  if (!dataset) return <div className="text-center py-20 text-gray-500">Dataset not found</div>

  const safetyCount = examples?.items?.filter(e => e.is_safety_tagged).length ?? 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-300 transition-colors">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <PageHeader
          title={dataset.name}
          description={`v${dataset.version} · ${dataset.category} · ${dataset.example_count} examples`}
          action={
            <Button onClick={() => setAddOpen(true)}>
              <Plus className="h-4 w-4" /> Add Example
            </Button>
          }
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Examples', value: dataset.example_count },
          { label: 'Version', value: `v${dataset.version}` },
          { label: 'Category', value: dataset.category },
          { label: 'Safety Tagged', value: safetyCount, highlight: safetyCount > 0 },
        ].map(({ label, value, highlight }) => (
          <Card key={label}>
            <CardContent className="py-3">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p className={cn('text-xl font-bold', highlight ? 'text-red-400' : 'text-gray-100')}>
                {value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-gray-500" />
        <select
          className="text-sm rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-gray-300 focus:outline-none focus:border-indigo-500"
          value={difficulty}
          onChange={e => { setDifficulty(e.target.value); setOffset(0) }}
        >
          {DIFFICULTIES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
        </select>
        <select
          className="text-sm rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-gray-300 focus:outline-none focus:border-indigo-500"
          value={persona}
          onChange={e => { setPersona(e.target.value); setOffset(0) }}
        >
          {PERSONAS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
        {(difficulty || persona) && (
          <button
            onClick={() => { setDifficulty(''); setPersona(''); setOffset(0) }}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            Clear filters
          </button>
        )}
        <span className="text-xs text-gray-600 ml-auto">
          {examples?.total ?? 0} examples
        </span>
      </div>

      {/* Examples table */}
      <Card>
        {loadingExamples ? (
          <CardContent><Spinner /></CardContent>
        ) : !examples?.items?.length ? (
          <CardContent>
            <EmptyState
              title="No examples"
              description={difficulty || persona ? "No examples match your filters." : "Add your first example to this dataset."}
              action={!difficulty && !persona ? <Button onClick={() => setAddOpen(true)}>Add Example</Button> : undefined}
            />
          </CardContent>
        ) : (
          <>
            <Table>
              <Thead>
                <tr>
                  <Th className="w-10"></Th>
                  <Th>Query</Th>
                  <Th>Persona</Th>
                  <Th>Difficulty</Th>
                  <Th>Safety Tags</Th>
                  <Th>Added</Th>
                </tr>
              </Thead>
              <Tbody>
                {examples.items.map(example => (
                  <ExampleRow key={example.id} example={example} />
                ))}
              </Tbody>
            </Table>

            {/* Pagination */}
            {examples.total > LIMIT && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-white/5">
                <p className="text-xs text-gray-500">
                  Showing {offset + 1}–{Math.min(offset + LIMIT, examples.total)} of {examples.total}
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm" variant="outline"
                    disabled={offset === 0}
                    onClick={() => setOffset(o => Math.max(0, o - LIMIT))}
                  >
                    Previous
                  </Button>
                  <Button
                    size="sm" variant="outline"
                    disabled={!examples.has_more}
                    onClick={() => setOffset(o => o + LIMIT)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      <AddExampleModal
        datasetId={id!}
        open={addOpen}
        onClose={() => setAddOpen(false)}
      />
    </div>
  )
}
