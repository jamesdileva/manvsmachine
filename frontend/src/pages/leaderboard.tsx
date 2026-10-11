/** Leaderboard page: daily (by score) and all-time (by rating) boards (Sprint 22). */

import { useEffect, useState } from 'react'

import { LeaderboardTable } from '@/components/LeaderboardTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useLeaderboard } from '@/hooks/useLeaderboard'
import { cn } from '@/lib/utils'

type Board = 'daily' | 'all-time'

const TABS: { key: Board; label: string }[] = [
  { key: 'daily', label: 'Daily' },
  { key: 'all-time', label: 'All-time' },
]

export default function Leaderboard() {
  const { daily, allTime, isLoading, error, loadDaily, loadAllTime } =
    useLeaderboard()
  const [board, setBoard] = useState<Board>('daily')

  useEffect(() => {
    if (board === 'daily') {
      void loadDaily()
    } else {
      void loadAllTime()
    }
  }, [board, loadDaily, loadAllTime])

  const entries = board === 'daily' ? daily?.entries : allTime?.entries

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Leaderboard</h1>
      <div role="tablist" aria-label="Leaderboard range" className="flex gap-2">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`tab-${key}`}
            aria-selected={board === key}
            aria-controls="board-panel"
            onClick={() => setBoard(key)}
            className={cn(
              'inline-flex h-9 items-center rounded-md px-3 text-sm font-medium transition-colors',
              board === key
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
            )}
          >
            {label}
          </button>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle>
            {board === 'daily'
              ? `Daily — ${daily?.date ?? ''}`
              : 'All-time — Detection Rating'}
          </CardTitle>
        </CardHeader>
        <CardContent
          id="board-panel"
          role="tabpanel"
          aria-labelledby={`tab-${board}`}
        >
          {error ? (
            <p className="py-8 text-center text-sm text-destructive">{error}</p>
          ) : isLoading && !entries ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Loading the board…
            </p>
          ) : (
            <LeaderboardTable
              entries={entries ?? []}
              metric={board === 'daily' ? 'score' : 'rating'}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
