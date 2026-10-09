import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { toApiError } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/useAuth'

type Mode = 'signin' | 'register'

export default function Auth() {
  const { login, register, loginAsGuest } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<void>) {
    setError(null)
    setBusy(true)
    try {
      await action()
      navigate('/', { replace: true })
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">
        {mode === 'signin' ? 'Sign in' : 'Create account'}
      </h1>
      <Card className="max-w-sm">
        <CardHeader>
          <CardTitle>Player account</CardTitle>
          <CardDescription>
            Play as a guest instantly, or sign in to keep your Detection Rating
            across sessions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode === 'register' && (
            <Input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Display name"
              aria-label="Display name"
            />
          )}
          <Input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            aria-label="Email"
          />
          <Input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password"
            aria-label="Password"
          />
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            {mode === 'signin' ? (
              <Button
                disabled={busy}
                onClick={() => run(() => login(email, password))}
              >
                Sign in
              </Button>
            ) : (
              <Button
                disabled={busy}
                onClick={() =>
                  run(() => register(email, password, displayName))
                }
              >
                Create account
              </Button>
            )}
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => run(loginAsGuest)}
            >
              Continue as guest
            </Button>
          </div>
          <button
            type="button"
            className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            onClick={() => {
              setMode(mode === 'signin' ? 'register' : 'signin')
              setError(null)
            }}
          >
            {mode === 'signin'
              ? 'Need an account? Register'
              : 'Have an account? Sign in'}
          </button>
        </CardContent>
      </Card>
    </div>
  )
}
