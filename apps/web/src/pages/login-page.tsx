import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'

export function LoginPage() {
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()
  const { t } = useTranslation('auth')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : t('loginFailed'))
    } finally {
      setLoading(false)
    }
  }

  const demoUsers = [
    { user: 'admin', pw: 'admin123', labelKey: 'admin' },
    { user: 'operator1', pw: 'op123', labelKey: 'operator' },
    { user: 'reviewer1', pw: 'reviewer123', labelKey: 'reviewer' },
  ]

  const fillDemo = (u: string, p: string) => {
    setUsername(u)
    setPassword(p)
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardContent className="p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-foreground">{t('docStampSystem')}</h1>
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
                error={!!error}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" loading={loading} className="w-full">
              {loading ? t('loginInProgress') : t('login')}
            </Button>
          </form>

          <p className="text-sm text-center mt-5 text-muted-foreground">
            {t('noAccount')}{' '}
            <Link to="/register" className="text-primary hover:underline font-medium">
              {t('register')}
            </Link>
          </p>

          <div className="mt-6 pt-5 border-t border-border">
            <p className="text-xs text-muted-foreground text-center mb-2.5">{t('demoAccounts')}</p>
            <div className="flex gap-2">
              {demoUsers.map((d) => (
                <button
                  key={d.user}
                  onClick={() => fillDemo(d.user, d.pw)}
                  className="flex-1 py-1.5 text-xs bg-secondary text-secondary-foreground hover:bg-secondary/80 rounded-md transition cursor-pointer font-medium"
                >
                  {t(d.labelKey)}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
