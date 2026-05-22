import { Outlet } from 'react-router-dom'
import { useLocation } from 'react-router-dom'
import { CameraFeed } from '@/components/camera/camera-feed'
import { ChatWidget } from '@/components/chat-widget'
import { Sidebar } from './sidebar'

export function AppShell() {
  const location = useLocation()
  const isStampPage = location.pathname === '/'

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className={cn(isStampPage ? 'p-4 h-full' : 'max-w-[1200px] mx-auto px-6 py-8')}>
          <Outlet />
        </div>
      </main>
      {/* Camera feed persistence for non-stamp pages */}
      <div
        className={isStampPage ? 'hidden' : 'fixed bottom-0 right-0 w-px h-px opacity-0 pointer-events-none overflow-hidden'}
        aria-hidden={!isStampPage}
      >
        <CameraFeed />
      </div>
      <ChatWidget />
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}
