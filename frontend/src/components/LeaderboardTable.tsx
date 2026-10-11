/** LeaderboardTable: ranked rows, sortable by column (Sprint 22). */

import { useState } from 'react'

import type { LeaderboardEntry } from '@/types'

interface LeaderboardTableProps {
  entries: LeaderboardEntry[]
  /** Daily boards rank by `score`, all-time boards by `rating`. */
  metric: 'score' | 'rating'
}

type SortKey = 'rank' | 'display_name' | 'metric' | 'accuracy'

function cellValue(
  entry: LeaderboardEntry,
  key: SortKey,
  metric: 'score' | 'rating',
): number | string {
  switch (key) {
    case 'rank':
      return entry.rank
    case 'display_name':
      return entry.display_name
    case 'metric':
      return entry[metric] ?? -1
    case 'accuracy':
      return entry.accuracy ?? -1
  }
}

export function LeaderboardTable({ entries, metric }: LeaderboardTableProps) {
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({
    key: 'rank',
    desc: false,
  })

  if (entries.length === 0) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        No entries yet for this board.
      </p>
    )
  }

  const sorted = [...entries].sort((a, b) => {
    const [left, right] = [
      cellValue(a, sort.key, metric),
      cellValue(b, sort.key, metric),
    ]
    let order: number
    if (typeof left === 'string' || typeof right === 'string') {
      order = String(left).localeCompare(String(right))
    } else {
      order = left - right
    }
    return sort.desc ? -order : order
  })

  function toggle(key: SortKey) {
    setSort((current) => {
      if (current.key === key) {
        return { key, desc: !current.desc }
      }
      // Numeric columns read best descending on first click; rank/name rise.
      return { key, desc: key === 'metric' || key === 'accuracy' }
    })
  }

  function header(key: SortKey, label: string) {
    const active = sort.key === key
    return (
      <th
        scope="col"
        aria-sort={active ? (sort.desc ? 'descending' : 'ascending') : 'none'}
      >
        <button
          type="button"
          onClick={() => toggle(key)}
          className="inline-flex items-center gap-1 font-medium hover:text-foreground"
        >
          {label}
          {active && <span aria-hidden>{sort.desc ? '▾' : '▴'}</span>}
        </button>
      </th>
    )
  }

  return (
    <table className="w-full text-sm">
      <caption className="sr-only">
        {metric === 'score' ? 'Daily' : 'All-time'} leaderboard
      </caption>
      <thead>
        <tr className="border-b text-left text-muted-foreground">
          {header('rank', 'Rank')}
          {header('display_name', 'Player')}
          {header('metric', metric === 'score' ? 'Score' : 'Rating')}
          {header('accuracy', 'Accuracy')}
        </tr>
      </thead>
      <tbody>
        {sorted.map((entry) => (
          <tr
            key={entry.user_id}
            data-testid="leaderboard-row"
            className="border-b last:border-0"
          >
            <td className="py-2 pr-4 tabular-nums">{entry.rank}</td>
            <td className="py-2 pr-4" data-testid="leaderboard-name">
              {entry.display_name}
            </td>
            <td className="py-2 pr-4 tabular-nums">{entry[metric] ?? '—'}</td>
            <td className="py-2 pr-4 tabular-nums">
              {entry.accuracy === null ? '—' : `${entry.accuracy.toFixed(1)}%`}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
