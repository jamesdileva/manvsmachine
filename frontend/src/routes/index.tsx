import { Route, Routes } from 'react-router-dom'

import { Layout } from '@/components/layout'
import Auth from '@/pages/auth'
import Challenge from '@/pages/challenge'
import Home from '@/pages/home'
import Leaderboard from '@/pages/leaderboard'
import Profile from '@/pages/profile'
import Session from '@/pages/session'
import Settings from '@/pages/settings'

/** All seven routes (Implementation Guide §8) inside the shared layout. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="session" element={<Session />} />
        <Route path="challenge" element={<Challenge />} />
        <Route path="leaderboard" element={<Leaderboard />} />
        <Route path="profile" element={<Profile />} />
        <Route path="auth" element={<Auth />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
