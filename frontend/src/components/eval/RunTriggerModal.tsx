import { useState, useEffect } from 'react'
import { useInstitutions, usePrograms, useAgents, useAgentVersions, useDatasets, useJudges, useJudgeVersions, useTriggerEvalRun } from '@/lib/api/hooks'
import { Button, Dialog, Spinner } from '@/components/ui'
import { cn } from '@/lib/utils'
import type { JudgeVersion } from '@/lib/api/types'

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: (runId: string) => void
}

interface Step {
  id: number
  label: string
  done: boolean
}

export function RunTriggerModal({ open, onClose, onSuccess }: Props) {
  const [institutionId, setInstitutionId] = useState('')
  const [programId, setProgramId] = useState('')
  const [agentId, setAgentId] = useState('')
  const [agentVersionId, setAgentVersionId] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [selectedJudgeVersionIds, setSelectedJudgeVersionIds] = useState<string[]>([])
  const [loadingJudgeVersions, setLoadingJudgeVersions] = useState(false)
  const [allJudgeVersions, setAllJudgeVersions] = useState<(JudgeVersion & { judge_name: string; judge_slug: string; is_safety_critical: boolean })[]>([])

  const { data: institutions, isLoading: loadingInstitutions } = useInstitutions()
  const { data: programs } = usePrograms(institutionId)
  const { data: agents } = useAgents(programId)
  const { data: agentVersions } = useAgentVersions(agentId)
  const { data: datasets } = useDatasets(programId)
  const { data: judges } = useJudges()
  const trigger = useTriggerEvalRun()

  // Reset downstream when upstream changes
  useEffect(() => { setProgramId(''); setAgentId(''); setAgentVersionId(''); setDatasetId('') }, [institutionId])
  useEffect(() => { setAgentId(''); setAgentVersionId(''); setDatasetId('') }, [programId])
  useEffect(() => { setAgentVersionId('') }, [agentId])

  // Auto-select latest version when agent is chosen
  useEffect(() => {
    if (agentVersions?.items?.length) {
      setAgentVersionId(agentVersions.items[0].id)
    }
  }, [agentVersions])

  // Load all judge versions when judges are loaded
  useEffect(() => {
    if (!judges?.items?.length) return
    setLoadingJudgeVersions(true)

    const fetchAll = async () => {
      const { api } = await import('@/lib/api/client')
      const results = []
      for (const judge of judges.items) {
        try {
          const res = await api.get<any>(`/v1/judges/${judge.id}/versions?limit=1`)
          if (res.items?.[0]) {
            results.push({
              ...res.items[0],
              judge_name: judge.name,
              judge_slug: judge.slug,
              is_safety_critical: judge.is_safety_critical,
            })
          }
        } catch {}
      }
      setAllJudgeVersions(results)
      // Auto-select all quality judges
      const qualityIds = results.filter(j => !j.is_safety_critical).map(j => j.id)
      setSelectedJudgeVersionIds(qualityIds)
      setLoadingJudgeVersions(false)
    }

    fetchAll()
  }, [judges])

  const toggleJudge = (id: string) => {
    setSelectedJudgeVersionIds(prev =>
      prev.includes(id) ? prev.filter(j => j !== id) : [...prev, id]
    )
  }

  const handleTrigger = async () => {
    const run = await trigger.mutateAsync({
      agent_version_id: agentVersionId,
      dataset_id: datasetId,
      judge_version_ids: selectedJudgeVersionIds,
    })
    onSuccess(run.id)
    onClose()
  }

  const canTrigger = agentVersionId && datasetId && selectedJudgeVersionIds.length > 0

  const steps: Step[] = [
    { id: 1, label: 'Institution', done: !!institutionId },
    { id: 2, label: 'Program', done: !!programId },
    { id: 3, label: 'Agent & Version', done: !!agentVersionId },
    { id: 4, label: 'Dataset', done: !!datasetId },
    { id: 5, label: 'Judges', done: selectedJudgeVersionIds.length > 0 },
  ]

  return (
    <Dialog open={open} onClose={onClose} title="Trigger Eval Run" size="lg">
      {/* Progress steps */}
      <div className="flex items-center gap-1 mb-6">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-center gap-1 flex-1">
            <div className={cn(
              'h-6 w-6 rounded-full text-xs font-semibold flex items-center justify-center flex-shrink-0',
              step.done ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
            )}>
              {step.done ? '✓' : step.id}
            </div>
            <span className={cn('text-xs truncate', step.done ? 'text-green-700' : 'text-gray-400')}>
              {step.label}
            </span>
            {i < steps.length - 1 && <div className="flex-1 h-px bg-gray-200 mx-1" />}
          </div>
        ))}
      </div>

      <div className="space-y-4">
        {/* Institution */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Institution</label>
          {loadingInstitutions ? <Spinner size="sm" /> : (
            <select
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
              value={institutionId}
              onChange={e => setInstitutionId(e.target.value)}
            >
              <option value="">Select institution…</option>
              {institutions?.items?.map(i => (
                <option key={i.id} value={i.id}>{i.name}</option>
              ))}
            </select>
          )}
        </div>

        {/* Program */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Program</label>
          <select
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white disabled:bg-gray-50 disabled:text-gray-400"
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

        {/* Agent + Version */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Agent</label>
            <select
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white disabled:bg-gray-50 disabled:text-gray-400"
              value={agentId}
              onChange={e => setAgentId(e.target.value)}
              disabled={!programId}
            >
              <option value="">Select agent…</option>
              {agents?.items?.map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
            <select
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white disabled:bg-gray-50 disabled:text-gray-400"
              value={agentVersionId}
              onChange={e => setAgentVersionId(e.target.value)}
              disabled={!agentId}
            >
              <option value="">Select version…</option>
              {agentVersions?.items?.map(v => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} — {v.model_id}{v.is_locked ? ' (locked)' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Dataset */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Dataset</label>
          <select
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white disabled:bg-gray-50 disabled:text-gray-400"
            value={datasetId}
            onChange={e => setDatasetId(e.target.value)}
            disabled={!programId}
          >
            <option value="">Select dataset…</option>
            {datasets?.items?.map(d => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.example_count} examples, v{d.version})
              </option>
            ))}
          </select>
        </div>

        {/* Judges */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Judges
            <span className="ml-2 text-xs text-gray-400 font-normal">
              {selectedJudgeVersionIds.length} selected
            </span>
          </label>
          {loadingJudgeVersions ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Spinner size="sm" /> Loading judges…
            </div>
          ) : (
            <div className="space-y-2">
              {/* Quality judges */}
              <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">Quality</p>
              <div className="grid grid-cols-3 gap-2">
                {allJudgeVersions.filter(j => !j.is_safety_critical).map(j => (
                  <JudgeToggle
                    key={j.id}
                    name={j.judge_name}
                    selected={selectedJudgeVersionIds.includes(j.id)}
                    onClick={() => toggleJudge(j.id)}
                    isSafety={false}
                  />
                ))}
              </div>
              {/* Safety-critical judges */}
              <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mt-3">Safety Critical</p>
              <div className="grid grid-cols-3 gap-2">
                {allJudgeVersions.filter(j => j.is_safety_critical).map(j => (
                  <JudgeToggle
                    key={j.id}
                    name={j.judge_name}
                    selected={selectedJudgeVersionIds.includes(j.id)}
                    onClick={() => toggleJudge(j.id)}
                    isSafety={true}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Summary */}
        {canTrigger && (
          <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600 space-y-1 border">
            <p><span className="font-medium">Agent version:</span> {agentVersions?.items?.find(v => v.id === agentVersionId)?.version_number ? `v${agentVersions.items.find(v => v.id === agentVersionId)!.version_number}` : agentVersionId.slice(0, 8)}</p>
            <p><span className="font-medium">Dataset:</span> {datasets?.items?.find(d => d.id === datasetId)?.name} ({datasets?.items?.find(d => d.id === datasetId)?.example_count} examples)</p>
            <p><span className="font-medium">Judges:</span> {allJudgeVersions.filter(j => selectedJudgeVersionIds.includes(j.id)).map(j => j.judge_name).join(', ')}</p>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleTrigger}
            loading={trigger.isPending}
            disabled={!canTrigger}
          >
            Trigger Eval Run
          </Button>
        </div>
      </div>
    </Dialog>
  )
}

function JudgeToggle({ name, selected, onClick, isSafety }: {
  name: string
  selected: boolean
  onClick: () => void
  isSafety: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-3 py-2 rounded-lg text-xs font-medium text-left transition-all border',
        selected
          ? isSafety
            ? 'bg-red-50 border-red-300 text-red-800'
            : 'bg-beacon-50 border-beacon-300 text-beacon-800'
          : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700'
      )}
    >
      {selected && <span className="mr-1">✓</span>}
      {name}
    </button>
  )
}
