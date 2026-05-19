import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/auth-store'
import { useUIStore } from '@/stores/ui-store'
import { cn } from '@/lib/utils'
import { useConnectionStore } from '@/stores/connection-store'
import {
  Stamp,
  FileText,
  ScrollText,
  CheckSquare,
  LayoutTemplate,
  Users,
  BarChart3,
  Settings,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Languages,
} from 'lucide-react'

interface NavItem {
  path: string
  labelKey: string
  ns: string
  icon: typeof Stamp
  roles?: string[]
}

const navGroups: NavItem[][] = [
  [
    { path: '/', labelKey: 'dashboard', ns: 'nav', icon: Stamp },
    { path: '/applications', labelKey: 'leaveApplications', ns: 'nav', icon: FileText },
  ],
  [
    { path: '/logs', labelKey: 'auditLogs', ns: 'nav', icon: ScrollText, roles: ['admin', 'reviewer'] },
    { path: '/review', labelKey: 'manualReview', ns: 'nav', icon: CheckSquare, roles: ['admin', 'reviewer'] },
  ],
  [
    { path: '/admin/templates', labelKey: 'templateManagement', ns: 'nav', icon: LayoutTemplate, roles: ['admin'] },
    { path: '/admin/users', labelKey: 'userManagement', ns: 'nav', icon: Users, roles: ['admin'] },
    { path: '/stats', labelKey: 'statsPanel', ns: 'nav', icon: BarChart3, roles: ['admin'] },
    { path: '/calibration', labelKey: 'armCalibration', ns: 'nav', icon: Settings, roles: ['admin'] },
  ],
]

export function Sidebar() {
  const location = useLocation()
  const { t } = useTranslation('nav')
  const { user, logout } = useAuthStore()
  const { sidebarCollapsed, toggleSidebar, locale, setLocale } = useUIStore()
  const connectionStatus = useConnectionStore((s) => s.status)

  function isActive(path: string) {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <aside
      className={cn(
        'flex h-screen flex-col border-r border-sidebar-border bg-sidebar-background transition-[width] duration-200 ease-out shrink-0 overflow-hidden',
        sidebarCollapsed ? 'w-[56px]' : 'w-[240px]'
      )}
    >
      {/* Header */}
      <div className="flex h-14 items-center gap-3 px-4 border-b border-sidebar-border shrink-0">
        {!sidebarCollapsed && (
          <div className="animate-fade-in flex min-w-0 items-center gap-2">
            <span className="text-base font-bold tracking-tight text-foreground">{t('appName')}</span>
            {connectionStatus !== 'connected' && (
              <span
                className={cn(
                  'inline-block h-2 w-2 rounded-full shrink-0',
                  connectionStatus === 'connecting'
                    ? 'bg-yellow-500 animate-pulse'
                    : 'bg-red-500',
                )}
              />
            )}
          </div>
        )}
        {sidebarCollapsed && connectionStatus !== 'connected' && (
          <span
            className={cn(
              'mx-auto inline-block h-2 w-2 rounded-full shrink-0',
              connectionStatus === 'connecting'
                ? 'bg-yellow-500 animate-pulse'
                : 'bg-red-500',
            )}
          />
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-md text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors cursor-pointer shrink-0"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {navGroups.map((group, gi) => (
          <div key={gi} className={cn(gi > 0 && 'mt-4')}>
            {group
              .filter((item) => !item.roles || (user && item.roles.includes(user.role)))
              .map((item) => {
                const active = isActive(item.path)
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={cn(
                      'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-100 ease-out',
                      active
                        ? 'bg-primary/8 text-primary'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                      active && 'border-l-2 border-primary'
                    )}
                    title={sidebarCollapsed ? t(item.labelKey) : undefined}
                  >
                    <item.icon className="h-4 w-4 shrink-0" />
                    {!sidebarCollapsed && (
                      <span className="truncate animate-fade-in">{t(item.labelKey)}</span>
                    )}
                  </Link>
                )
              })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-2 space-y-1 shrink-0">
        {/* Language toggle */}
        <button
          onClick={() => setLocale(locale === 'zh' ? 'en' : 'zh')}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors cursor-pointer"
          title={sidebarCollapsed ? (locale === 'zh' ? 'English' : '中文') : undefined}
        >
          <Languages className="h-4 w-4 shrink-0" />
          {!sidebarCollapsed && (
            <span className="truncate animate-fade-in">
              {locale === 'zh' ? 'English' : '中文'}
            </span>
          )}
        </button>

        {/* User info + logout */}
        {user && (
          <div className={cn('flex items-center gap-3 px-3 py-2', !sidebarCollapsed && 'min-w-0')}>
            <div className="h-6 w-6 shrink-0 rounded-full bg-primary/15 flex items-center justify-center">
              <span className="text-xs font-semibold text-primary">
                {user.username.charAt(0).toUpperCase()}
              </span>
            </div>
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0 animate-fade-in">
                <p className="text-sm font-medium text-foreground truncate">{user.username}</p>
                <p className="text-xs text-muted-foreground truncate">{user.role}</p>
              </div>
            )}
            <button
              onClick={logout}
              className="p-1 rounded text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors cursor-pointer shrink-0"
              title={t('logout')}
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
