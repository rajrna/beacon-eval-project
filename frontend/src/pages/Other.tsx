// Programs.tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInstitutions, usePrograms, useCreateProgram } from '@/lib/api/hooks'
import { Button, Card, PageHeader, EmptyState, Table, Thead, Tbody, Th, Td, Badge, Dialog, Input, Select, Spinner } from '@/components/ui'
import { formatDate } from '@/lib/utils'

export function Programs() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [selectedInstitution, setSelectedInstitution] = useState('')
  const [form, setForm] = useState({ name: '', degree_type: '', format: 'online', modality: 'async', term_calendar: 'semester', description: '' })
  const { data: institutions } = useInstitutions()
  const { data: programs, isLoading } = usePrograms(selectedInstitution)
  const create = useCreateProgram()

  const handleCreate = async () => {
    await create.mutateAsync({ ...form, institution_id: selectedInstitution })
    setOpen(false)
  }

  return (
    <div>
      <PageHeader title="Programs" description="Degree programs across all institutions"
        action={<Button onClick={() => setOpen(true)}>+ New Program</Button>} />
      <div className="mb-4">
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          value={selectedInstitution} onChange={e => setSelectedInstitution(e.target.value)}>
          <option value="">Select institution…</option>
          {institutions?.items?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
      </div>
      {isLoading ? <Spinner /> : (
        <Card>
          {!programs?.items?.length ? <div className="px-6 py-8"><EmptyState title="No programs" description="Select an institution or create a program." /></div> : (
            <Table><Thead><tr><Th>Name</Th><Th>Degree</Th><Th>Format</Th><Th>Agents</Th><Th>Datasets</Th><Th>Created</Th></tr></Thead>
              <Tbody>{programs.items.map(p => (
                <tr key={p.id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/programs/${p.id}`)}>
                  <Td className="font-medium">{p.name}</Td><Td>{p.degree_type}</Td>
                  <Td><Badge variant="info">{p.format}</Badge></Td>
                  <Td>{p.agent_count}</Td><Td>{p.dataset_count}</Td>
                  <Td className="text-gray-500">{formatDate(p.created_at)}</Td>
                </tr>))}</Tbody></Table>)}
        </Card>)}
      <Dialog open={open} onClose={() => setOpen(false)} title="New Program">
        <div className="space-y-4">
          <Select label="Institution" value={selectedInstitution} onChange={e => setSelectedInstitution(e.target.value)}
            options={[{ value: '', label: 'Select…' }, ...(institutions?.items?.map(i => ({ value: i.id, label: i.name })) ?? [])]} />
          <Input label="Program Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Online MBA" />
          <Input label="Degree Type" value={form.degree_type} onChange={e => setForm(f => ({ ...f, degree_type: e.target.value }))} placeholder="MBA" />
          <div className="flex gap-3 pt-2 justify-end">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={create.isPending}>Create</Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}

// Agents.tsx
import { useAgents, usePrograms as usePrograms2, useInstitutions as useInstitutions2 } from '@/lib/api/hooks'

export function Agents() {
  const navigate = useNavigate()
  const [programId, setProgramId] = useState('')
  const [institutionId, setInstitutionId] = useState('')
  const { data: institutions } = useInstitutions2()
  const { data: programs } = usePrograms2(institutionId)
  const { data: agents, isLoading } = useAgents(programId)

  return (
    <div>
      <PageHeader title="Agents" description="Student-facing AI agents" />
      <div className="flex gap-3 mb-4">
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          value={institutionId} onChange={e => { setInstitutionId(e.target.value); setProgramId('') }}>
          <option value="">Select institution…</option>
          {institutions?.items?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          value={programId} onChange={e => setProgramId(e.target.value)} disabled={!institutionId}>
          <option value="">Select program…</option>
          {programs?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>
      {isLoading ? <Spinner /> : (
        <Card>
          {!agents?.items?.length ? <div className="px-6 py-8"><EmptyState title="No agents" description="Select a program to see its agents." /></div> : (
            <Table><Thead><tr><Th>Name</Th><Th>Role</Th><Th>Versions</Th><Th>Active</Th><Th>Created</Th></tr></Thead>
              <Tbody>{agents.items.map(a => (
                <tr key={a.id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/agents/${a.id}`)}>
                  <Td className="font-medium">{a.name}</Td>
                  <Td><Badge variant="purple">{a.role}</Badge></Td>
                  <Td>{a.version_count}</Td>
                  <Td><Badge variant={a.is_active ? 'success' : 'default'}>{a.is_active ? 'Active' : 'Inactive'}</Badge></Td>
                  <Td className="text-gray-500">{formatDate(a.created_at)}</Td>
                </tr>))}</Tbody></Table>)}
        </Card>)}
    </div>
  )
}

// Datasets.tsx  
import { useDatasets, useInstitutions as useInstitutions3, usePrograms as usePrograms3 } from '@/lib/api/hooks'

export function Datasets() {
  const navigate = useNavigate()
  const [institutionId, setInstitutionId] = useState('')
  const [programId, setProgramId] = useState('')
  const { data: institutions } = useInstitutions3()
  const { data: programs } = usePrograms3(institutionId)
  const { data: datasets, isLoading } = useDatasets(programId)

  return (
    <div>
      <PageHeader title="Datasets" description="Curated golden example datasets" />
      <div className="flex gap-3 mb-4">
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          value={institutionId} onChange={e => { setInstitutionId(e.target.value); setProgramId('') }}>
          <option value="">Select institution…</option>
          {institutions?.items?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          value={programId} onChange={e => setProgramId(e.target.value)} disabled={!institutionId}>
          <option value="">Select program…</option>
          {programs?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>
      {isLoading ? <Spinner /> : (
        <Card>
          {!datasets?.items?.length ? <div className="px-6 py-8"><EmptyState title="No datasets" description="Select a program to see its datasets." /></div> : (
            <Table><Thead><tr><Th>Name</Th><Th>Category</Th><Th>Version</Th><Th>Examples</Th><Th>Updated</Th></tr></Thead>
              <Tbody>{datasets.items.map(d => (
                <tr key={d.id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/datasets/${d.id}`)}>
                  <Td className="font-medium">{d.name}</Td>
                  <Td><Badge variant="info">{d.category}</Badge></Td>
                  <Td>v{d.version}</Td><Td>{d.example_count}</Td>
                  <Td className="text-gray-500">{formatDate(d.updated_at)}</Td>
                </tr>))}</Tbody></Table>)}
        </Card>)}
    </div>
  )
}

// Judges.tsx
import { useJudges as useJudges2, useJudgeVersions } from '@/lib/api/hooks'

export function Judges() {
  const { data: judges, isLoading } = useJudges2()

  return (
    <div>
      <PageHeader title="Judges" description="LLM-as-judge rubrics for evaluating agent responses" />
      {isLoading ? <Spinner /> : (
        <Card>
          {!judges?.items?.length ? <div className="px-6 py-8"><EmptyState title="No judges" /></div> : (
            <Table><Thead><tr><Th>Name</Th><Th>Slug</Th><Th>Type</Th><Th>Safety Critical</Th><Th>Versions</Th><Th>Active</Th></tr></Thead>
              <Tbody>{judges.items.map(j => (
                <tr key={j.id} className="hover:bg-gray-50">
                  <Td className="font-medium">{j.name}</Td>
                  <Td><code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{j.slug}</code></Td>
                  <Td><Badge variant="info">{j.judge_type}</Badge></Td>
                  <Td>{j.is_safety_critical ? <Badge variant="danger">Yes</Badge> : <Badge>No</Badge>}</Td>
                  <Td>{j.version_count}</Td>
                  <Td><Badge variant={j.is_active ? 'success' : 'default'}>{j.is_active ? 'Active' : 'Inactive'}</Badge></Td>
                </tr>))}</Tbody></Table>)}
        </Card>)}
    </div>
  )
}

// TraceBrowser.tsx
import { useState as useState2 } from 'react'
import { useTraces, useAgents as useAgents2, useInstitutions as useInstitutions4, usePrograms as usePrograms4 } from '@/lib/api/hooks'

export function TraceBrowser() {
  const navigate = useNavigate()
  const [institutionId, setInstitutionId] = useState2('')
  const [programId, setProgramId] = useState2('')
  const [agentId, setAgentId] = useState2('')
  const [agentVersionId, setAgentVersionId] = useState2('')
  const [needsReview, setNeedsReview] = useState2<boolean | undefined>(undefined)
  const { data: institutions } = useInstitutions4()
  const { data: programs } = usePrograms4(institutionId)
  const { data: agents } = useAgents2(programId)
  const { data: traces, isLoading } = useTraces(agentVersionId, needsReview)

  return (
    <div>
      <PageHeader title="Trace Browser" description="Production traces from student agent interactions" />
      <div className="flex flex-wrap gap-3 mb-4">
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          value={institutionId} onChange={e => { setInstitutionId(e.target.value); setProgramId(''); setAgentId(''); setAgentVersionId('') }}>
          <option value="">Institution…</option>
          {institutions?.items?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm" disabled={!institutionId}
          value={programId} onChange={e => { setProgramId(e.target.value); setAgentId(''); setAgentVersionId('') }}>
          <option value="">Program…</option>
          {programs?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm" disabled={!programId}
          value={agentId} onChange={e => { setAgentId(e.target.value); setAgentVersionId('') }}>
          <option value="">Agent…</option>
          {agents?.items?.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        {agentId && agents?.items?.find(a => a.id === agentId)?.latest_version_id && (
          <button className="text-sm text-beacon-600 hover:underline"
            onClick={() => setAgentVersionId(agents!.items.find(a => a.id === agentId)!.latest_version_id!)}>
            Use latest version
          </button>
        )}
        <select className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          value={needsReview === undefined ? '' : String(needsReview)}
          onChange={e => setNeedsReview(e.target.value === '' ? undefined : e.target.value === 'true')}>
          <option value="">All traces</option>
          <option value="true">Needs review</option>
          <option value="false">Reviewed</option>
        </select>
      </div>
      {isLoading ? <Spinner /> : (
        <Card>
          {!traces?.items?.length ? <div className="px-6 py-8"><EmptyState title="No traces" description="Select an agent version to browse traces." /></div> : (
            <Table><Thead><tr><Th>Trace ID</Th><Th>FERPA</Th><Th>Flags</Th><Th>Review</Th><Th>Captured</Th></tr></Thead>
              <Tbody>{traces.items.map(t => (
                <tr key={t.id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/traces/${t.id}`)}>
                  <Td><code className="text-xs">{t.id.slice(0, 8)}…</code></Td>
                  <Td><Badge variant={t.ferpa_classification === 'confidential' ? 'danger' : t.ferpa_classification === 'directory' ? 'warning' : 'default'}>{t.ferpa_classification}</Badge></Td>
                  <Td>{t.safety_flags.length > 0 ? <Badge variant="danger">{t.safety_flags.length} flags</Badge> : <span className="text-gray-400 text-xs">none</span>}</Td>
                  <Td>{t.needs_review ? <Badge variant="warning">Needs review</Badge> : <Badge variant="success">Clear</Badge>}</Td>
                  <Td className="text-gray-500 text-xs">{formatDate(t.created_at)}</Td>
                </tr>))}</Tbody></Table>)}
        </Card>)}
    </div>
  )
}

// Settings.tsx
import { useAuth as useAuth2 } from '@/lib/auth/useAuth'

export function Settings() {
  const { user, logout } = useAuth2()
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
                  <dd className="font-medium">{v}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-4 pt-4 border-t">
              <Button variant="danger" onClick={logout}>Sign Out</Button>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>About Beacon</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600">Student Agent Evaluation & Observability Platform</p>
            <p className="text-xs text-gray-400 mt-1">v0.1.0 — Phase 1</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
