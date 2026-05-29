import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Building2 } from 'lucide-react'
import { useInstitutions, useCreateInstitution } from '@/lib/api/hooks'
import {
  Button, Card, CardContent, PageHeader, EmptyState,
  Table, Thead, Tbody, Th, Td, Badge, Dialog, Input, Spinner,
} from '@/components/ui'
import { formatDate } from '@/lib/utils'

export default function Institutions() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', slug: '', accreditor: '', ipeds_id: '' })
  const { data, isLoading } = useInstitutions()
  const create = useCreateInstitution()

  const handleCreate = async () => {
    await create.mutateAsync(form)
    setOpen(false)
    setForm({ name: '', slug: '', accreditor: '', ipeds_id: '' })
  }

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>

  return (
    <div>
      <PageHeader
        title="Institutions"
        description="Universities and colleges registered in Beacon"
        action={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />New Institution</Button>}
      />

      <Card>
        {(!data?.items?.length) ? (
          <CardContent>
            <EmptyState
              title="No institutions yet"
              description="Register your first university to get started."
              action={<Button onClick={() => setOpen(true)}>Register Institution</Button>}
            />
          </CardContent>
        ) : (
          <Table>
            <Thead>
              <tr>
                <Th>Name</Th>
                <Th>Slug</Th>
                <Th>Accreditor</Th>
                <Th>Programs</Th>
                <Th>Created</Th>
              </tr>
            </Thead>
            <Tbody>
              {data.items.map(inst => (
                <tr
                  key={inst.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => navigate(`/institutions/${inst.id}`)}
                >
                  <Td>
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-8 rounded bg-beacon-100 flex items-center justify-center">
                        <Building2 className="h-4 w-4 text-beacon-600" />
                      </div>
                      <span className="font-medium text-gray-900">{inst.name}</span>
                    </div>
                  </Td>
                  <Td><code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{inst.slug}</code></Td>
                  <Td>{inst.accreditor ?? '—'}</Td>
                  <Td><Badge variant="info">{inst.program_count}</Badge></Td>
                  <Td className="text-gray-500">{formatDate(inst.created_at)}</Td>
                </tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} title="Register Institution">
        <div className="space-y-4">
          <Input label="Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Westbrook State University" />
          <Input label="Slug" value={form.slug} onChange={e => setForm(f => ({ ...f, slug: e.target.value }))} placeholder="westbrook-state" hint="Lowercase letters, numbers, and hyphens only" />
          <Input label="Accreditor" value={form.accreditor} onChange={e => setForm(f => ({ ...f, accreditor: e.target.value }))} placeholder="HLC" />
          <Input label="IPEDS ID" value={form.ipeds_id} onChange={e => setForm(f => ({ ...f, ipeds_id: e.target.value }))} placeholder="999001" />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={create.isPending}>Create</Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
