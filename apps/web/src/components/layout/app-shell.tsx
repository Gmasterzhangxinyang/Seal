import { Link, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { cn } from '@/lib/utils'
import { CameraFeed } from '@/components/camera/camera-feed'

const navItems = [
  { path: '/', label: '操作台' },
  { path: '/applications', label: '请假申请' },
  { path: '/logs', label: '审计日志', roles: ['admin', 'reviewer'] },
  { path: '/review', label: '人工复审', roles: ['admin', 'reviewer'] },
  { path: '/admin/templates', label: '模板管理', roles: ['admin'] },
  { path: '/admin/users', label: '用户管理', roles: ['admin'] },
  { path: '/stats', label: '统计面板', roles: ['admin'] },
  { path: '/calibration', label: '机械臂标定', roles: ['admin'] },
]

export function AppShell() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const isStampPage = location.pathname === '/'

  const visibleNavItems = navItems.filter(
    (item) => !item.roles || (user && item.roles.includes(user.role))
  )

  return (
    <div className="min-h-screen bg-background">
      {/* 顶部导航 */}
      <nav className="bg-[#1d3557] text-white flex items-center justify-between px-8 h-14 shadow-lg">
        <span className="text-lg font-bold tracking-wide">文档盖章机器人</span>
        <div className="flex items-center gap-6">
          {visibleNavItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'text-[#a8dadc] hover:text-white transition-colors text-sm',
                location.pathname === item.path && 'text-white font-semibold'
              )}
            >
              {item.label}
            </Link>
          ))}
          <div className="flex items-center gap-3 ml-4 pl-4 border-l border-[#a8dadc]/30">
            <span className="text-[#a8dadc] text-sm">
              {user?.username} · {user?.role}
            </span>
            <button
              onClick={logout}
              className="text-[#a8dadc] hover:text-white text-sm transition-colors"
            >
              退出
            </button>
          </div>
        </div>
      </nav>

      {/* 主内容区 */}
      <main className="max-w-[960px] mx-auto px-4 py-6">
        <Outlet />
      </main>

      {/* 持久摄像头流 — 仅在非操作台页面时隐藏 */}
      <div
        className={cn(
          isStampPage
            ? 'hidden'
            : 'fixed bottom-0 right-0 w-px h-px opacity-0 pointer-events-none overflow-hidden'
        )}
        aria-hidden={!isStampPage}
      >
        <CameraFeed />
      </div>
    </div>
  )
}
