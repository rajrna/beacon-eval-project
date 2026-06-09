import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Upload, FileText, Trash2, AlertCircle, CheckCircle,
  Clock, Loader2, BookOpen, ChevronDown, ChevronUp,
} from 'lucide-react'
import { api } from '@/lib/api/client'
import { Card, CardHeader, CardTitle, CardContent, Spinner } from '@/components/ui'
import { useInstitutions, usePrograms } from '@/lib/api/hooks'
import { formatDate, cn } from '@/lib/utils'

interface ProgramDocument {
  id: string
  filename: string
  category: string
  description: string | null
  file_size_bytes: number | null
  chunk_count: number | null
  status: 'processing' | 'ready' | 'failed'
  error_message: string | null
  created_at: string | null
}

const CATEGORIES = [
  { value: 'general', label: 'General' },
  { value: 'admissions', label: 'Admissions' },
  { value: 'financial_aid', label: 'Financial Aid' },
  { value: 'policies', label: 'Policies & Handbook' },
  { value: 'clinical', label: 'Clinical Education' },
  { value: 'career', label: 'Career & Residency' },
  { value: 'requirements', label: 'Requirements' },
]

function useDocuments(programId: string | null) {
  return useQuery({
    queryKey: ['documents', programId],
    queryFn: () => api.get<ProgramDocument[]>(`/v1/programs/${programId}/documents`),
    enabled: Boolean(programId),
    refetchInterval: (data) => {
      // Poll every 3s while any document is processing
      const docs = data as ProgramDocument[] | undefined
      if (docs?.some(d => d.status === 'processing')) return 3000
      return false
    },
  })
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'ready') return (
    <span className="flex items-center gap-1 text-xs text-green-400">
      <CheckCircle className="h-3 w-3" /> Ready
    </span>
  )
  if (status === 'processing') return (
    <span className="flex items-center gap-1 text-xs text-yellow-400">
      <Loader2 className="h-3 w-3 animate-spin" /> Processing
    </span>
  )
  return (
    <span className="flex items-center gap-1 text-xs text-red-400">
      <AlertCircle className="h-3 w-3" /> Failed
    </span>
  )
}

function DocumentRow({
  doc,
  onDelete,
}: {
  doc: ProgramDocument
  onDelete: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="px-4 py-3 hover:bg-white/3 transition-colors">
      <div className="flex items-start gap-3">
        <FileText className={cn(
          'h-5 w-5 flex-shrink-0 mt-0.5',
          doc.status === 'ready' ? 'text-indigo-400' :
          doc.status === 'processing' ? 'text-yellow-400' : 'text-red-400'
        )} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-gray-200 truncate">{doc.filename}</p>
            <StatusBadge status={doc.status} />
          </div>

          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-gray-600">
              {CATEGORIES.find(c => c.value === doc.category)?.label || doc.category}
            </span>
            {doc.chunk_count != null && doc.chunk_count > 0 && (
              <span className="text-xs text-gray-600">{doc.chunk_count} chunks</span>
            )}
            <span className="text-xs text-gray-600">{formatBytes(doc.file_size_bytes)}</span>
            {doc.created_at && (
              <span className="text-xs text-gray-700">{formatDate(doc.created_at)}</span>
            )}
          </div>

          {doc.description && (
            <p className="text-xs text-gray-500 mt-1">{doc.description}</p>
          )}

          {doc.status === 'failed' && doc.error_message && (
            <div className="mt-2 p-2 bg-red-900/20 border border-red-800 rounded text-xs text-red-400">
              {doc.error_message}
            </div>
          )}
        </div>

        <button
          onClick={() => onDelete(doc.id)}
          className="p-1.5 rounded text-gray-600 hover:text-red-400 hover:bg-red-900/20 transition-colors flex-shrink-0"
          title="Delete document"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}

export default function DocumentUpload() {
  const [institutionId, setInstitutionId] = useState('')
  const [programId, setProgramId] = useState('')
  const [category, setCategory] = useState('general')
  const [description, setDescription] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const { data: institutions } = useInstitutions()
  const { data: programs } = usePrograms(institutionId)
  const { data: documents, isLoading } = useDocuments(programId || null)

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      setUploadError(null)
      const formData = new FormData()
      formData.append('file', file)
      const url = `/v1/programs/${programId}/documents?category=${category}${description ? `&description=${encodeURIComponent(description)}` : ''}`
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${url}`, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer dev-token' },
        body: formData,
      })
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Upload failed')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', programId] })
      setDescription('')
    },
    onError: (err: Error) => {
      setUploadError(err.message)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (docId: string) =>
      api.delete(`/v1/programs/${programId}/documents/${docId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', programId] })
    },
  })

  const handleFile = (file: File) => {
    if (!file.name.endsWith('.pdf')) {
      setUploadError('Only PDF files are supported.')
      return
    }
    if (file.size > 20 * 1024 * 1024) {
      setUploadError('File too large. Maximum size is 20MB.')
      return
    }
    uploadMutation.mutate(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const readyCount = documents?.filter(d => d.status === 'ready').length || 0
  const totalChunks = documents?.filter(d => d.status === 'ready')
    .reduce((sum, d) => sum + (d.chunk_count || 0), 0) || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Documents</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload PDF documents to enhance RAG — chunks are automatically embedded and searched alongside knowledge entries
        </p>
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

      {programId && (
        <>
          {/* Stats */}
          {documents && documents.length > 0 && (
            <div className="grid grid-cols-3 gap-4">
              <Card>
                <CardContent className="py-4">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-indigo-900/30 flex items-center justify-center">
                      <FileText className="h-4 w-4 text-indigo-400" />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Documents</p>
                      <p className="text-xl font-bold text-gray-100">{readyCount}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-green-900/20 flex items-center justify-center">
                      <BookOpen className="h-4 w-4 text-green-400" />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Total chunks</p>
                      <p className="text-xl font-bold text-gray-100">{totalChunks}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-blue-900/20 flex items-center justify-center">
                      <Clock className="h-4 w-4 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Processing</p>
                      <p className="text-xl font-bold text-gray-100">
                        {documents.filter(d => d.status === 'processing').length}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Upload area */}
          <Card>
            <CardHeader>
              <CardTitle>Upload PDF</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Category + description */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Category</label>
                  <select
                    className="w-full text-sm rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-gray-300"
                    value={category}
                    onChange={e => setCategory(e.target.value)}
                  >
                    {CATEGORIES.map(c => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Description (optional)</label>
                  <input
                    type="text"
                    className="w-full text-sm rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
                    placeholder="e.g. HMS Student Handbook 2025"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                  />
                </div>
              </div>

              {/* Drop zone */}
              <div
                className={cn(
                  'border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer',
                  dragOver ? 'border-indigo-500 bg-indigo-900/20' : 'border-white/10 hover:border-white/20',
                  uploadMutation.isPending && 'pointer-events-none opacity-60',
                )}
                onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={e => {
                    const file = e.target.files?.[0]
                    if (file) handleFile(file)
                    e.target.value = ''
                  }}
                />

                {uploadMutation.isPending ? (
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 className="h-8 w-8 text-indigo-400 animate-spin" />
                    <p className="text-sm text-gray-400">Processing document…</p>
                    <p className="text-xs text-gray-600">Extracting text, chunking, and embedding. This may take 30–60 seconds.</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="h-8 w-8 text-gray-600" />
                    <p className="text-sm font-medium text-gray-300">
                      Drop a PDF here or click to browse
                    </p>
                    <p className="text-xs text-gray-600">PDF only · Max 20MB</p>
                  </div>
                )}
              </div>

              {/* Error */}
              {uploadError && (
                <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-800 rounded-lg">
                  <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                  <p className="text-sm text-red-400">{uploadError}</p>
                </div>
              )}

              {/* Success */}
              {uploadMutation.isSuccess && (
                <div className="flex items-center gap-2 p-3 bg-green-900/20 border border-green-800 rounded-lg">
                  <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0" />
                  <p className="text-sm text-green-400">
                    Document uploaded successfully — {(uploadMutation.data as any)?.chunks} chunks embedded and ready for RAG
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Documents list */}
          <Card>
            <CardHeader>
              <CardTitle>
                Uploaded Documents
                {documents && documents.length > 0 && (
                  <span className="ml-2 text-sm font-normal text-gray-500">({documents.length})</span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Spinner size="lg" />
                </div>
              ) : !documents || documents.length === 0 ? (
                <div className="px-6 py-12 text-center">
                  <FileText className="h-10 w-10 text-gray-700 mx-auto mb-3" />
                  <p className="text-sm font-medium text-gray-400">No documents uploaded yet</p>
                  <p className="text-xs text-gray-600 mt-1">
                    Upload a PDF above to enhance the knowledge base with full document content
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {documents.map(doc => (
                    <DocumentRow
                      key={doc.id}
                      doc={doc}
                      onDelete={(id) => deleteMutation.mutate(id)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {!programId && (
        <Card>
          <CardContent className="py-16 text-center">
            <BookOpen className="h-10 w-10 text-gray-700 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-400">No program selected</p>
            <p className="text-xs text-gray-600 mt-1">
              Select an institution and program above to manage documents
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
