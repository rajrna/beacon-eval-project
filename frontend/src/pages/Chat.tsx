import { useState, useRef, useEffect } from 'react'
import { Send, AlertTriangle, Shield, Bot, User, Loader2 } from 'lucide-react'
import { useAgents, useAgentVersions, useInstitutions, usePrograms } from '@/lib/api/hooks'
import { api } from '@/lib/api/client'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  safety_flagged?: boolean
  review_priority?: string
  trace_id?: string
}

interface ChatResponse {
  response: string
  trace_id: string | null
  safety_flagged: boolean
  review_priority: string | null
}

function SafetyBanner({ priority }: { priority: string }) {
  if (priority === 'crisis') {
    return (
      <div className="mx-4 mb-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
        <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-red-800">You're not alone</p>
          <p className="text-sm text-red-700 mt-0.5">
            If you're going through a difficult time, please reach out for support.
            Call or text <strong>988</strong> (Suicide & Crisis Lifeline) — available 24/7.
            Campus counseling is also available at ext. 5555.
          </p>
        </div>
      </div>
    )
  }
  if (priority === 'concerning') {
    return (
      <div className="mx-4 mb-3 p-3 bg-orange-50 border border-orange-200 rounded-lg flex items-start gap-2">
        <Shield className="h-4 w-4 text-orange-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-orange-800">
          A student success advisor has been notified and will follow up with you shortly.
        </p>
      </div>
    )
  }
  return null
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-3 px-4 py-2', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div className={cn(
        'h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0',
        isUser ? 'bg-beacon-600' : 'bg-gray-100'
      )}>
        {isUser
          ? <User className="h-4 w-4 text-white" />
          : <Bot className="h-4 w-4 text-gray-600" />
        }
      </div>

      {/* Bubble */}
      <div className={cn(
        'max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
        isUser
          ? 'bg-beacon-600 text-white rounded-tr-sm'
          : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm',
        message.safety_flagged && !isUser && 'border-orange-200 bg-orange-50'
      )}>
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.safety_flagged && !isUser && (
          <div className="flex items-center gap-1 mt-2 pt-2 border-t border-orange-200">
            <Shield className="h-3 w-3 text-orange-500" />
            <span className="text-xs text-orange-600">Flagged for review</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Chat() {
  const [institutionId, setInstitutionId] = useState('')
  const [programId, setProgramId] = useState('')
  const [agentId, setAgentId] = useState('')
  const [agentVersionId, setAgentVersionId] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => crypto.randomUUID())
  const [lastSafetyPriority, setLastSafetyPriority] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const { data: institutions } = useInstitutions()
  const { data: programs } = usePrograms(institutionId)
  const { data: agents } = useAgents(programId)
  const { data: agentVersions } = useAgentVersions(agentId)

  // Auto-select latest version
  useEffect(() => {
    if (agentVersions?.items?.length) {
      setAgentVersionId(agentVersions.items[0].id)
    }
  }, [agentVersions])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const selectedAgent = agents?.items?.find(a => a.id === agentId)

  const handleSend = async () => {
    if (!input.trim() || !agentVersionId || loading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setLastSafetyPriority(null)

    try {
      const allMessages = [...messages, userMessage]
      const result = await api.post<ChatResponse>('/v1/chat', {
        messages: allMessages.map(m => ({ role: m.role, content: m.content })),
        agent_version_id: agentVersionId,
        session_id: sessionId,
      })

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.response,
        safety_flagged: result.safety_flagged,
        review_priority: result.review_priority || undefined,
        trace_id: result.trace_id || undefined,
      }

      setMessages(prev => [...prev, assistantMessage])

      if (result.safety_flagged && result.review_priority) {
        setLastSafetyPriority(result.review_priority)
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: "I'm sorry, I'm having trouble responding right now. Please try again or contact admissions directly.",
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isReady = Boolean(agentVersionId)

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-beacon-600 flex items-center justify-center">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 text-sm">
              {selectedAgent?.name || 'Student Advisor'}
            </p>
            <p className="text-xs text-gray-500">Westbrook State University</p>
          </div>
          {isReady && (
            <span className="flex items-center gap-1 text-xs text-green-600 ml-2">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
              Online
            </span>
          )}
        </div>

        {/* Agent selector */}
        <div className="flex items-center gap-2">
          <select
            className="text-xs rounded-md border border-gray-200 px-2 py-1.5 bg-white text-gray-600"
            value={institutionId}
            onChange={e => { setInstitutionId(e.target.value); setProgramId(''); setAgentId(''); setAgentVersionId('') }}
          >
            <option value="">Institution…</option>
            {institutions?.items?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
          </select>
          <select
            className="text-xs rounded-md border border-gray-200 px-2 py-1.5 bg-white text-gray-600"
            value={programId}
            onChange={e => { setProgramId(e.target.value); setAgentId(''); setAgentVersionId('') }}
            disabled={!institutionId}
          >
            <option value="">Program…</option>
            {programs?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select
            className="text-xs rounded-md border border-gray-200 px-2 py-1.5 bg-white text-gray-600"
            value={agentId}
            onChange={e => setAgentId(e.target.value)}
            disabled={!programId}
          >
            <option value="">Agent…</option>
            {agents?.items?.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full py-20 text-center px-8">
            <div className="h-16 w-16 rounded-full bg-beacon-100 flex items-center justify-center mb-4">
              <Bot className="h-8 w-8 text-beacon-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              {selectedAgent ? `Chat with ${selectedAgent.name}` : 'Select an agent to start'}
            </h2>
            <p className="text-sm text-gray-500 max-w-sm">
              {selectedAgent
                ? "Ask anything about admissions, tuition, program requirements, or student support."
                : "Choose an institution, program, and agent from the dropdowns above."}
            </p>
            {selectedAgent && (
              <div className="mt-6 grid grid-cols-2 gap-2 w-full max-w-md">
                {[
                  "What are the admission requirements?",
                  "How much does the MBA cost?",
                  "Can I take a leave of absence?",
                  "What financial aid is available?",
                ].map(suggestion => (
                  <button
                    key={suggestion}
                    onClick={() => { setInput(suggestion); inputRef.current?.focus() }}
                    className="text-xs text-left px-3 py-2 rounded-lg border border-gray-200 bg-white hover:border-beacon-300 hover:bg-beacon-50 text-gray-600 hover:text-beacon-700 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {loading && (
          <div className="flex gap-3 px-4 py-2">
            <div className="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
              <Bot className="h-4 w-4 text-gray-600" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1 items-center">
                <span className="h-2 w-2 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="h-2 w-2 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="h-2 w-2 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Safety banner */}
      {lastSafetyPriority && (
        <SafetyBanner priority={lastSafetyPriority} />
      )}

      {/* Input */}
      <div className="bg-white border-t px-4 py-3">
        <div className={cn(
          'flex items-end gap-3 rounded-xl border px-3 py-2 transition-colors',
          isReady ? 'border-gray-300 focus-within:border-beacon-400' : 'border-gray-200 bg-gray-50'
        )}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isReady ? "Ask anything about the MBA program…" : "Select an agent above to start chatting"}
            disabled={!isReady || loading}
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-gray-800 placeholder-gray-400 focus:outline-none disabled:cursor-not-allowed"
            style={{ maxHeight: '120px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !isReady || loading}
            className={cn(
              'h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors',
              input.trim() && isReady && !loading
                ? 'bg-beacon-600 text-white hover:bg-beacon-700'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            )}
          >
            {loading
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Send className="h-4 w-4" />
            }
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1.5 text-center">
          Press Enter to send · Shift+Enter for new line
          {messages.length > 0 && (
            <span className="ml-2">· Session: {sessionId.slice(0, 8)}…</span>
          )}
        </p>
      </div>
    </div>
  )
}
