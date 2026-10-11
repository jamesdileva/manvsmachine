import {
  Home,
  LayoutDashboard,
  LogIn,
  LogOut,
  Medal,
  Settings,
  Trophy,
  User,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { profileApi } from '@/api/profile'
import { Button } from '@/components/ui/button'
import { StreakBadge } from '@/components/StreakBadge'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/session', label: 'Session', icon: LayoutDashboard },
  { to: '/challenge', label: 'Challenge', icon: Trophy },
  { to: '/leaderboard', label: 'Leaderboard', icon: Medal },
  { to: '/profile', label: 'Profile', icon: User },
  { to: '/auth', label: 'Auth', icon: LogIn },
  { to: '/settings', label: 'Settings', icon: Settings },
]

/** Nav streak chip; guests get nothing extra (profile is auth-only). */
function NavStreak() {
  const { isAuthenticated } = useAuth()
  const [streak, setStreak] = useState<number | null>(null)
  useEffect(() => {
    if (!isAuthenticated) return
    void profileApi
      .get()
      .then((profile) => setStreak(profile.current_streak))
      .catch(() => setStreak(null))
  }, [isAuthenticated])
  if (streak === null) return null
  return <StreakBadge days={streak} />
}

export function Layout() {
  const { user, isAuthenticated, logout } = useAuth()
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container flex h-14 items-center justify-between">
          <NavLink to="/" className="font-bold">
            Man vs. Machine
          </NavLink>
          <nav className="flex items-center gap-1" aria-label="Main navigation">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'inline-flex h-9 items-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground',
                    isActive
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground',
                  )
                }
              >
                <Icon className="h-4 w-4" aria-hidden />
                {label}
              </NavLink>
            ))}
            {isAuthenticated && (
              <div className="ml-2 flex items-center gap-2 border-l pl-2">
                <NavStreak />
                <span
                  className="text-sm text-muted-foreground"
                  data-testid="nav-user"
                >
                  {user?.display_name}
                </span>
                <Button variant="ghost" size="sm" onClick={logout}>
                  <LogOut className="h-4 w-4" aria-hidden />
                  Log out
                </Button>
              </div>
            )}
          </nav>
        </div>
      </header>
      <main className="container py-6">
        <Outlet />
      </main>
    </div>
  )
}
