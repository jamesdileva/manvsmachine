import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactElement } from 'react'

import { Layout } from '@/components/layout'
import { useAuthContext } from '@/contexts/AuthContext'
import Auth from '@/pages/auth'
import Challenge from '@/pages/challenge'
import Home from '@/pages/home'
import Leaderboard from '@/pages/leaderboard'
import NotFound from '@/pages/not-found'
import Profile from '@/pages/profile'
import Session from '@/pages/session'
import Settings from '@/pages/settings'

/** Gate for signed-in routes: shows a loading hint, then redirects to /auth. */
function RequireAuth({ children }: { children: ReactElement }) {
  const { isAuthenticated, isLoading } = useAuthContext()
  if (isLoading) {
    return (
      <div className="py-10 text-center text-muted-foreground">
        Loading your session…
      </div>
    )
  }
  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />
  }
  return children
}

/** All seven routes (Implementation Guide §8) inside the shared layout. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="auth" element={<Auth />} />
        <Route
          path="session"
          element={
            <RequireAuth>
              <Session />
            </RequireAuth>
          }
        />
        <Route
          path="challenge"
          element={
            <RequireAuth>
              <Challenge />
            </RequireAuth>
          }
        />
        <Route
          path="leaderboard"
          element={
            <RequireAuth>
              <Leaderboard />
            </RequireAuth>
          }
        />
        <Route
          path="profile"
          element={
            <RequireAuth>
              <Profile />
            </RequireAuth>
          }
        />
        <Route
          path="settings"
          element={
            <RequireAuth>
              <Settings />
            </RequireAuth>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
