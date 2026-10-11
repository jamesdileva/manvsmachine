import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { LeaderboardTable } from '@/components/LeaderboardTable'
import type { LeaderboardEntry } from '@/types'

const daily: LeaderboardEntry[] = [
  {
    rank: 1,
    user_id: 'u1',
    display_name: 'Alex',
    score: 300,
    rating: null,
    accuracy: 100,
  },
  {
    rank: 2,
    user_id: 'u2',
    display_name: 'Jordan',
    score: 275,
    rating: null,
    accuracy: 66.7,
  },
  {
    rank: 3,
    user_id: 'u3',
    display_name: 'Morgan',
    score: 350,
    rating: null,
    accuracy: 33.3,
  },
]

function names() {
  return screen
    .getAllByTestId('leaderboard-row')
    .map(
      (row) =>
        row.querySelector('[data-testid="leaderboard-name"]')?.textContent,
    )
}

describe('LeaderboardTable', () => {
  it('shows one row per entry with rank, name, score and accuracy', () => {
    render(<LeaderboardTable entries={daily} metric="score" />)

    const rows = screen.getAllByTestId('leaderboard-row')
    expect(rows).toHaveLength(3)
    expect(rows[0]).toHaveTextContent('Alex')
    expect(rows[0]).toHaveTextContent('300')
    expect(rows[0]).toHaveTextContent('100.0%')
  })

  it('shows the rating column for all-time boards', () => {
    render(
      <LeaderboardTable
        entries={[
          {
            rank: 1,
            user_id: 'u1',
            display_name: 'Morgan',
            score: null,
            rating: 1450,
            accuracy: 71.4,
          },
        ]}
        metric="rating"
      />,
    )
    expect(screen.getByTestId('leaderboard-row')).toHaveTextContent('1450')
    expect(screen.queryByText('300')).not.toBeInTheDocument()
  })

  it('sorts by score descending when the score header is clicked', async () => {
    render(<LeaderboardTable entries={daily} metric="score" />)
    expect(names()).toEqual(['Alex', 'Jordan', 'Morgan'])

    await userEvent.click(screen.getByRole('button', { name: /score/i }))

    expect(names()).toEqual(['Morgan', 'Alex', 'Jordan'])
  })

  it('sorts by name ascending then descending on repeat clicks', async () => {
    render(<LeaderboardTable entries={daily} metric="score" />)
    const header = screen.getByRole('button', { name: /player/i })

    await userEvent.click(header)
    expect(names()).toEqual(['Alex', 'Jordan', 'Morgan'])

    await userEvent.click(header)
    expect(names()).toEqual(['Morgan', 'Jordan', 'Alex'])
  })

  it('renders a message when the board is empty', () => {
    render(<LeaderboardTable entries={[]} metric="score" />)
    expect(screen.getByText(/no entries yet/i)).toBeInTheDocument()
  })
})
