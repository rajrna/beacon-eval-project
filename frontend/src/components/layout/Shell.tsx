import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Building2, GraduationCap, Bot, Database, Scale,
  PlayCircle, Activity, Inbox, Settings, Menu, X, AlertTriangle, MessageSquare,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth/useAuth'
import { Badge } from '@/components/ui'
import { useSmeQueue } from '@/lib/api/hooks'

const NAV_ITEMS = [
  { to: '/institutions', icon: Building2, label: 'Institutions' },
  { to: '/programs', icon: GraduationCap, label: 'Programs' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/datasets', icon: Database, label: 'Datasets' },
  { to: '/judges', icon: Scale, label: 'Judges' },
  { to: '/runs', icon: PlayCircle, label: 'Eval Runs' },
  { to: '/traces', icon: Activity, label: 'Traces' },
  { to: '/sme/queue', icon: Inbox, label: 'SME Queue' },
  { to: '/chat', icon: MessageSquare, label: 'Student Chat' },
]

export function Shell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout } = useAuth()
  const location = useLocation()

  // Show crisis count badge on SME Queue nav item
  const { data: crisisQueue } = useSmeQueue('queued', 'crisis')
  const crisisCount = crisisQueue?.items?.length ?? 0

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className={cn(
        'fixed inset-y-0 left-0 z-50 w-64 bg-white border-r flex flex-col transition-transform',
        'lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
      )}>
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-beacon-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">B</span>
            </div>
            <span className="font-semibold text-gray-900 text-lg">Beacon</span>
          </div>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-beacon-50 text-beacon-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {label === 'SME Queue' && crisisCount > 0 && (
                <span className="bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-bold">
                  {crisisCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User info */}
        <div className="border-t p-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-beacon-100 flex items-center justify-center text-beacon-700 font-semibold text-sm">
              {user.display_name[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{user.display_name}</p>
              <p className="text-xs text-gray-500 capitalize">{user.role}</p>
            </div>
            <button onClick={logout} className="text-gray-400 hover:text-gray-600">
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-16 bg-white border-b flex items-center px-4 lg:px-6 gap-4">
          <button className="lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-5 w-5 text-gray-500" />
          </button>
          <div className="flex-1" />
          {crisisCount > 0 && (
            <a href="/sme/queue?priority=crisis" className="flex items-center gap-1.5 text-red-600 text-sm font-medium animate-pulse">
              <AlertTriangle className="h-4 w-4" />
              {crisisCount} crisis {crisisCount === 1 ? 'trace' : 'traces'} awaiting review
            </a>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
