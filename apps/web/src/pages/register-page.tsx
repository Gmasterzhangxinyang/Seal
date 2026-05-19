import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'

export function RegisterPage() {
  const register = useAuthStore((s) => s.register)
  const navigate = useNavigate()
  const { t } = useTranslation('auth')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) {
      setError(t('passwordMismatch'))
      return
    }
    setLoading(true)
    try {
      await register(username, email, password)
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : t('registerFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardContent className="p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-foreground">{t('registerAccount')}</h1>
            <p className="mt-1 text-sm text-muted-foreground">MEC202</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5 text-foreground">{t('username')}</label>
              <Input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={2}
                maxLength={20}
                error={!!error}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5 text-foreground">{t('email')}</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                error={!!error}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5 text-foreground">{t('password')}</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                error={!!error}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5 text-foreground">{t('confirmPassword')}</label>
              <Input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={6}
                error={!!error}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" loading={loading} className="w-full">
              {loading ? t('registering') : t('register')}
            </Button>
          </form>

          <p className="text-sm text-center mt-5 text-muted-foreground">
            {t('hasAccount')}{' '}
            <Link to="/login" className="text-primary hover:underline font-medium">
              {t('goToLogin')}
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
