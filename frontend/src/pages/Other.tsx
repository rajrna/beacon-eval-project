import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useInstitutions, usePrograms, useAgents, useDatasets, useJudges,
  useCreateProgram, useCreateAgent, useCreateDataset,
} from '@/lib/api/hooks'
import {
  Button, Card, PageHeader, EmptyState, Table, Thead, Tbody, Th, Td,
  Badge, Dialog, Input, Select, Textarea, Spinner,
} from '@/components/ui'
import { formatDate } from '@/lib/utils'

// ── Shared institution+program selector ──────────────────────────────────────

function InstitutionProgramSelector({
  institutionId, setInstitutionId,
  programId, setProgramId,
  onInstitutionChange,
}: {
  institutionId: string
  setInstitutionId: (id: string) => void
  programId: string
  setProgramId: (id: string) => void
  onInstitutionChange?: () => void
}) {
  const { data: institutions } = useInstitutions()
  const { data: programs } = usePrograms(institutionId)
  return (
    <div className="flex gap-3 mb-4">
      <select
        className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300"
        value={institutionId}
        onChange={e => {
          setInstitutionId(e.target.value)
          setProgramId('')
          onInstitutionChange?.()
        }}
      >
        <option value="">Select institution…</option>
        {institutions?.items?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
      </select>
      <select
        className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300 disabled:opacity-50"
        value={programId}
        onChange={e => setProgramId(e.target.value)}
        disabled={!institutionId}
      >
        <option value="">Select program…</option>
        {programs?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>
    </div>
  )
}

// ── Programs ──────────────────────────────────────────────────────────────────

export function Programs() {
  const navigate = useNavigate()
  const [institutionId, setInstitutionId] = useState('')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    name: '', degree_type: '', format: 'online', modality: 'async',
    term_calendar: 'semester', tuition_per_credit: '', total_credits: '', description: '',
  })
  const { data: institutions } = useInstitutions()
  const { data: programs, isLoading } = usePrograms(institutionId)
  const create = useCreateProgram()

  const handleCreate = async () => {
    await create.mutateAsync({
      institution_id: institutionId,
      name: form.name,
      degree_type: form.degree_type,
      format: form.format,
      modality: form.modality,
      term_calendar: form.term_calendar,
      tuition_per_credit: form.tuition_per_credit ? parseFloat(form.tuition_per_credit) : undefined,
      total_credits: form.total_credits ? parseInt(form.total_credits) : undefined,
      description: form.description || undefined,
    })
    setOpen(false)
    setForm({ name: '', degree_type: '', format: 'online', modality: 'async', term_calendar: 'semester', tuition_per_credit: '', total_credits: '', description: '' })
  }

  return (
    <div>
      <PageHeader
        title="Programs"
        description="Degree programs across all institutions"
        action={
          <Button onClick={() => setOpen(true)} disabled={!institutionId}>
            + New Program
          </Button>
        }
      />
      <div className="mb-4">
        <select
          className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300"
          value={institutionId}
          onChange={e => setInstitutionId(e.target.value)}
        >
          <option value="">Select institution…</option>
          {institutions?.items?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        {!institutionId && <p className="text-xs text-gray-600 mt-1">Select an institution to see its programs</p>}
      </div>
      {isLoading ? <Spinner /> : (
        <Card>
          {!programs?.items?.length ? (
            <div className="px-6 py-8">
              <EmptyState
                title={institutionId ? "No programs yet" : "Select an institution"}
                description={institutionId ? "Create the first program for this institution." : "Choose an institution from the dropdown above."}
                action={institutionId ? <Button onClick={() => setOpen(true)}>New Program</Button> : undefined}
              />
            </div>
          ) : (
            <Table>
              <Thead><tr><Th>Name</Th><Th>Degree</Th><Th>Format</Th><Th>Tuition/Credit</Th><Th>Credits</Th><Th>Agents</Th><Th>Created</Th></tr></Thead>
              <Tbody>
                {programs.items.map(p => (
                  <tr key={p.id} className="cursor-pointer hover:bg-white/5 border-b border-white/5" onClick={() => navigate(`/programs/${p.id}`)}>
                    <Td className="font-medium text-gray-200">{p.name}</Td>
                    <Td><Badge variant="info">{p.degree_type}</Badge></Td>
                    <Td className="text-gray-400 text-sm">{p.format}</Td>
                    <Td className="text-gray-400 text-sm">{p.tuition_per_credit ? `$${p.tuition_per_credit}` : '—'}</Td>
                    <Td className="text-gray-400 text-sm">{p.total_credits ?? '—'}</Td>
                    <Td>{p.agent_count}</Td>
                    <Td className="text-gray-500 text-xs">{formatDate(p.created_at)}</Td>
                  </tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Card>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} title="New Program" size="lg">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Program Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Online MBA" />
            <Input label="Degree Type" value={form.degree_type} onChange={e => setForm(f => ({ ...f, degree_type: e.target.value }))} placeholder="MBA, BS, MS, AS…" />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Select label="Format" value={form.format} onChange={e => setForm(f => ({ ...f, format: e.target.value }))}
              options={[{ value: 'online', label: 'Online' }, { value: 'hybrid', label: 'Hybrid' }, { value: 'in-person', label: 'In-Person' }]} />
            <Select label="Modality" value={form.modality} onChange={e => setForm(f => ({ ...f, modality: e.target.value }))}
              options={[{ value: 'async', label: 'Async' }, { value: 'sync', label: 'Sync' }, { value: 'mixed', label: 'Mixed' }]} />
            <Select label="Term Calendar" value={form.term_calendar} onChange={e => setForm(f => ({ ...f, term_calendar: e.target.value }))}
              options={[{ value: 'semester', label: 'Semester' }, { value: 'quarter', label: 'Quarter' }, { value: 'eight-week', label: 'Eight-Week' }]} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Tuition per Credit ($)" type="number" value={form.tuition_per_credit} onChange={e => setForm(f => ({ ...f, tuition_per_credit: e.target.value }))} placeholder="750" />
            <Input label="Total Credits" type="number" value={form.total_credits} onChange={e => setForm(f => ({ ...f, total_credits: e.target.value }))} placeholder="36" />
          </div>
          <Textarea label="Description (optional)" rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={create.isPending} disabled={!form.name || !form.degree_type}>Create Program</Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}

// ── Agents ────────────────────────────────────────────────────────────────────

export function Agents() {
  const navigate = useNavigate()
  const [institutionId, setInstitutionId] = useState('')
  const [programId, setProgramId] = useState('')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    name: '', role: 'outreach', owner_team: '', owner_email: '', description: '',
  })
  const { data: agents, isLoading } = useAgents(programId)
  const create = useCreateAgent()

  const handleCreate = async () => {
    await create.mutateAsync({
      program_id: programId,
      name: form.name,
      role: form.role,
      owner_team: form.owner_team || undefined,
      owner_email: form.owner_email || undefined,
      description: form.description || undefined,
    })
    setOpen(false)
    setForm({ name: '', role: 'outreach', owner_team: '', owner_email: '', description: '' })
  }

  return (
    <div>
      <PageHeader
        title="Agents"
        description="Student-facing AI agents"
        action={
          <Button onClick={() => setOpen(true)} disabled={!programId}>
            + New Agent
          </Button>
        }
      />
      <InstitutionProgramSelector
        institutionId={institutionId} setInstitutionId={setInstitutionId}
        programId={programId} setProgramId={setProgramId}
      />
      {!programId && <p className="text-xs text-gray-600 mb-4">Select a program to see its agents</p>}
      {isLoading ? <Spinner /> : (
        <Card>
          {!agents?.items?.length ? (
            <div className="px-6 py-8">
              <EmptyState
                title={programId ? "No agents yet" : "Select a program"}
                description={programId ? "Create the first agent for this program." : "Choose an institution and program above."}
                action={programId ? <Button onClick={() => setOpen(true)}>New Agent</Button> : undefined}
              />
            </div>
          ) : (
            <Table>
              <Thead><tr><Th>Name</Th><Th>Role</Th><Th>Versions</Th><Th>Active</Th><Th>Owner</Th><Th>Created</Th></tr></Thead>
              <Tbody>
                {agents.items.map(a => (
                  <tr key={a.id} className="cursor-pointer hover:bg-white/5 border-b border-white/5" onClick={() => navigate(`/agents/${a.id}`)}>
                    <Td className="font-medium text-gray-200">{a.name}</Td>
                    <Td><Badge variant="purple">{a.role}</Badge></Td>
                    <Td className="text-gray-400">{a.version_count}</Td>
                    <Td><Badge variant={a.is_active ? 'success' : 'default'}>{a.is_active ? 'Active' : 'Inactive'}</Badge></Td>
                    <Td className="text-gray-500 text-sm">{a.owner_team ?? '—'}</Td>
                    <Td className="text-gray-500 text-xs">{formatDate(a.created_at)}</Td>
                  </tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Card>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} title="New Agent" size="md">
        <div className="space-y-4">
          <Input label="Agent Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="MBA Enrollment Bot" />
          <Select
            label="Role"
            value={form.role}
            onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
            options={[
              { value: 'advisor', label: 'Advisor' },
              { value: 'outreach', label: 'Outreach' },
              { value: 'retention', label: 'Retention' },
              { value: 'finaid', label: 'Financial Aid' },
              { value: 'career', label: 'Career' },
              { value: 'tutor', label: 'Tutor' },
            ]}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Owner Team" value={form.owner_team} onChange={e => setForm(f => ({ ...f, owner_team: e.target.value }))} placeholder="Enrollment Engineering" />
            <Input label="Owner Email" value={form.owner_email} onChange={e => setForm(f => ({ ...f, owner_email: e.target.value }))} placeholder="team@college.edu" />
          </div>
          <Textarea label="Description (optional)" rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <p className="text-xs text-gray-500">After creating the agent, go to its detail page to add a system prompt version.</p>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={create.isPending} disabled={!form.name}>Create Agent</Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}

// ── Datasets ──────────────────────────────────────────────────────────────────

export function Datasets() {
  const navigate = useNavigate()
  const [institutionId, setInstitutionId] = useState('')
  const [programId, setProgramId] = useState('')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', category: 'tuition', description: '' })
  const { data: datasets, isLoading } = useDatasets(programId)
  const create = useCreateDataset()

  const handleCreate = async () => {
    await create.mutateAsync({
      program_id: programId,
      name: form.name,
      category: form.category,
      description: form.description || undefined,
    })
    setOpen(false)
    setForm({ name: '', category: 'tuition', description: '' })
  }

  return (
    <div>
      <PageHeader
        title="Datasets"
        description="Curated golden example datasets"
        action={
          <Button onClick={() => setOpen(true)} disabled={!programId}>
            + New Dataset
          </Button>
        }
      />
      <InstitutionProgramSelector
        institutionId={institutionId} setInstitutionId={setInstitutionId}
        programId={programId} setProgramId={setProgramId}
      />
      {!programId && <p className="text-xs text-gray-600 mb-4">Select a program to see its datasets</p>}
      {isLoading ? <Spinner /> : (
        <Card>
          {!datasets?.items?.length ? (
            <div className="px-6 py-8">
              <EmptyState
                title={programId ? "No datasets yet" : "Select a program"}
                description={programId ? "Create the first dataset for this program." : "Choose an institution and program above."}
                action={programId ? <Button onClick={() => setOpen(true)}>New Dataset</Button> : undefined}
              />
            </div>
          ) : (
            <Table>
              <Thead><tr><Th>Name</Th><Th>Category</Th><Th>Version</Th><Th>Examples</Th><Th>Updated</Th></tr></Thead>
              <Tbody>
                {datasets.items.map(d => (
                  <tr key={d.id} className="cursor-pointer hover:bg-white/5 border-b border-white/5" onClick={() => navigate(`/datasets/${d.id}`)}>
                    <Td className="font-medium text-gray-200">{d.name}</Td>
                    <Td><Badge variant="info">{d.category}</Badge></Td>
                    <Td className="text-gray-400">v{d.version}</Td>
                    <Td className="text-gray-400">{d.example_count}</Td>
                    <Td className="text-gray-500 text-xs">{formatDate(d.updated_at)}</Td>
                  </tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Card>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} title="New Dataset" size="md">
        <div className="space-y-4">
          <Input label="Dataset Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Admissions Q&A" />
          <Select
            label="Category"
            value={form.category}
            onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
            options={[
              { value: 'tuition', label: 'Tuition' },
              { value: 'admissions', label: 'Admissions' },
              { value: 'retention', label: 'Retention' },
              { value: 'safety', label: 'Safety / Adversarial' },
              { value: 'career', label: 'Career' },
              { value: 'finaid', label: 'Financial Aid' },
            ]}
          />
          <Textarea label="Description (optional)" rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={create.isPending} disabled={!form.name}>Create Dataset</Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}

// ── Judges ────────────────────────────────────────────────────────────────────

export function Judges() {
  const { data: judges, isLoading } = useJudges()
  return (
    <div>
      <PageHeader title="Judges" description="LLM-as-judge rubrics for evaluating agent responses" />
      {isLoading ? <Spinner /> : (
        <Card>
          {!judges?.items?.length ? (
            <div className="px-6 py-8"><EmptyState title="No judges" description="Run the seed script to register the built-in judges." /></div>
          ) : (
            <Table>
              <Thead><tr><Th>Name</Th><Th>Slug</Th><Th>Type</Th><Th>Safety Critical</Th><Th>Versions</Th><Th>Active</Th></tr></Thead>
              <Tbody>
                {judges.items.map(j => (
                  <tr key={j.id} className="hover:bg-white/5 border-b border-white/5">
                    <Td className="font-medium text-gray-200">{j.name}</Td>
                    <Td><code className="text-xs bg-white/5 px-1.5 py-0.5 rounded text-gray-400">{j.slug}</code></Td>
                    <Td><Badge variant="info">{j.judge_type}</Badge></Td>
                    <Td>{j.is_safety_critical ? <Badge variant="danger">Yes</Badge> : <Badge>No</Badge>}</Td>
                    <Td className="text-gray-400">{j.version_count}</Td>
                    <Td><Badge variant={j.is_active ? 'success' : 'default'}>{j.is_active ? 'Active' : 'Inactive'}</Badge></Td>
                  </tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Card>
      )}
    </div>
  )
}

// ── TraceBrowser ──────────────────────────────────────────────────────────────

import { useInstitutions as useInstitutions2, usePrograms as usePrograms2, useAgents as useAgents2, useTraces } from '@/lib/api/hooks'

export function TraceBrowser() {
  const navigate = useNavigate()
  const [institutionId, setInstitutionId] = useState('')
  const [programId, setProgramId] = useState('')
  const [agentId, setAgentId] = useState('')
  const [agentVersionId, setAgentVersionId] = useState('')
  const [needsReview, setNeedsReview] = useState<boolean | undefined>(undefined)
  const { data: institutions } = useInstitutions2()
  const { data: programs } = usePrograms2(institutionId)
  const { data: agents } = useAgents2(programId)
  const { data: traces, isLoading } = useTraces(agentVersionId, needsReview)

  return (
    <div>
      <PageHeader title="Trace Browser" description="Production traces from student agent interactions" />
      <div className="flex flex-wrap gap-3 mb-4">
        <select className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300"
          value={institutionId} onChange={e => { setInstitutionId(e.target.value); setProgramId(''); setAgentId(''); setAgentVersionId('') }}>
          <option value="">Institution…</option>
          {institutions?.items?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        <select className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300 disabled:opacity-50"
          value={programId} onChange={e => { setProgramId(e.target.value); setAgentId(''); setAgentVersionId('') }} disabled={!institutionId}>
          <option value="">Program…</option>
          {programs?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300 disabled:opacity-50"
          value={agentId} onChange={e => { setAgentId(e.target.value); setAgentVersionId('') }} disabled={!programId}>
          <option value="">Agent…</option>
          {agents?.items?.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        {agentId && agents?.items?.find(a => a.id === agentId)?.latest_version_id && (
          <button className="text-sm text-indigo-400 hover:text-indigo-300 hover:underline"
            onClick={() => setAgentVersionId(agents!.items.find(a => a.id === agentId)!.latest_version_id!)}>
            Use latest version
          </button>
        )}
        <select className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300"
          value={needsReview === undefined ? '' : String(needsReview)}
          onChange={e => setNeedsReview(e.target.value === '' ? undefined : e.target.value === 'true')}>
          <option value="">All traces</option>
          <option value="true">Needs review</option>
          <option value="false">Reviewed</option>
        </select>
      </div>
      {isLoading ? <Spinner /> : (
        <Card>
          {!traces?.items?.length ? (
            <div className="px-6 py-8">
              <EmptyState title="No traces" description="Select an agent version to browse traces." />
            </div>
          ) : (
            <Table>
              <Thead><tr><Th>Trace ID</Th><Th>FERPA</Th><Th>Flags</Th><Th>Review</Th><Th>Captured</Th></tr></Thead>
              <Tbody>
                {traces.items.map(t => (
                  <tr key={t.id} className="cursor-pointer hover:bg-white/5 border-b border-white/5" onClick={() => navigate(`/traces/${t.id}`)}>
                    <Td><code className="text-xs text-gray-400">{t.id.slice(0, 8)}…</code></Td>
                    <Td><Badge variant={t.ferpa_classification === 'confidential' ? 'danger' : t.ferpa_classification === 'directory' ? 'warning' : 'default'}>{t.ferpa_classification}</Badge></Td>
                    <Td>{t.safety_flags.length > 0 ? <Badge variant="danger">{t.safety_flags.length} flags</Badge> : <span className="text-gray-600 text-xs">none</span>}</Td>
                    <Td>{t.needs_review ? <Badge variant="warning">Needs review</Badge> : <Badge variant="success">Clear</Badge>}</Td>
                    <Td className="text-gray-500 text-xs">{formatDate(t.created_at)}</Td>
                  </tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Card>
      )}
    </div>
  )
}

// ── Settings ──────────────────────────────────────────────────────────────────

import { useAuth } from '@/lib/auth/useAuth'
import { CardHeader, CardTitle, CardContent } from '@/components/ui'

export function Settings() {
  const { user, logout } = useAuth()
  return (
    <div>
      <PageHeader title="Settings" />
      <div className="max-w-lg space-y-6">
        <Card>
          <CardHeader><CardTitle>Your Account</CardTitle></CardHeader>
          <CardContent>
            <dl className="space-y-3 text-sm">
              {[['Name', user.display_name], ['Email', user.email], ['Role', user.role], ['User ID', user.id]].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-gray-500">{k}</dt>
                  <dd className="font-medium text-gray-200">{v}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-4 pt-4 border-t border-white/10">
              <Button variant="danger" onClick={logout}>Sign Out</Button>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>About Beacon</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-gray-400">Student Agent Evaluation & Observability Platform</p>
            <p className="text-xs text-gray-600 mt-1">v0.1.0 — Phase 1</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
