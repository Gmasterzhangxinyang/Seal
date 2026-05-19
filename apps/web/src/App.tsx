import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { startConnectionMonitor } from '@/stores/connection-store'
import { AppShell } from '@/components/layout/app-shell'
import { LoginPage } from '@/pages/login-page'
import { RegisterPage } from '@/pages/register-page'
import { StampPage } from '@/pages/stamp-page'
import { LogsPage } from '@/pages/logs-page'
import { ReviewPage } from '@/pages/review-page'
import { TemplatesPage } from '@/pages/templates-page'
import { TemplateEditPage } from '@/pages/template-edit-page'
import { StatsPage } from '@/pages/stats-page'
import { CalibrationPage } from '@/pages/calibration-page'
import { UsersPage } from '@/pages/users-page'
import { LeaveApplicationsPage } from '@/pages/LeaveApplicationsPage'
import { NewLeaveApplicationPage } from '@/pages/NewLeaveApplicationPage'
import { LeaveApplicationDetailPage } from '@/pages/LeaveApplicationDetailPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuthStore()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-9 h-9 border-4 border-gray-200 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth)

  useEffect(() => {
    const publicPaths = ['/login', '/register']
    if (!publicPaths.some((p) => window.location.pathname.startsWith(p))) {
      checkAuth()
    } else {
      useAuthStore.setState({ loading: false })
    }
    const timer = startConnectionMonitor()
    return () => clearInterval(timer)
  }, [checkAuth])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<StampPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/admin/templates" element={<TemplatesPage />} />
          <Route path="/admin/templates/new" element={<TemplateEditPage />} />
          <Route path="/admin/templates/:id/edit" element={<TemplateEditPage />} />
          <Route path="/stats" element={<StatsPage />} />
          <Route path="/calibration" element={<CalibrationPage />} />
          <Route path="/admin/users" element={<UsersPage />} />
          <Route path="/applications" element={<LeaveApplicationsPage />} />
          <Route path="/applications/new" element={<NewLeaveApplicationPage />} />
          <Route path="/applications/:applicationId" element={<LeaveApplicationDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
