import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { SessionSummary } from '@/components/SessionSummary'
import type { SessionSummaryResponse } from '@/types'

const summary: SessionSummaryResponse = {
  session_id: 's1',
  type: 'daily',
  total_score: 345,
  accuracy: 66.7,
  rounds: [
    {
      round_number: 1,
      challenge_id: 'challenge_slogan_01',
      vote: 'B',
      correct: true,
      score: 115,
      humanity_human: 100,
      humanity_ai: 0,
    },
    {
      round_number: 2,
      challenge_id: 'challenge_emoji_03',
      vote: 'A',
      correct: false,
      score: 15,
      humanity_human: 0,
      humanity_ai: 100,
    },
    {
      round_number: 3,
      challenge_id: 'challenge_tweet_09',
      vote: 'B',
      correct: true,
      score: 215,
      humanity_human: 100,
      humanity_ai: 0,
    },
  ],
  rating_change: null,
  streak: 1,
}

function renderSummary() {
  return render(
    <MemoryRouter>
      <SessionSummary summary={summary} />
    </MemoryRouter>,
  )
}

describe('SessionSummary', () => {
  it('shows the totals', () => {
    renderSummary()
    expect(screen.getByTestId('summary-total')).toHaveTextContent('345')
    expect(screen.getByTestId('summary-accuracy')).toHaveTextContent('67%')
    expect(screen.getByTestId('summary-streak')).toHaveTextContent('1')
  })

  it('lists the per-round breakdown', () => {
    renderSummary()
    const items = screen.getByTestId('summary-rounds').querySelectorAll('li')
    expect(items).toHaveLength(3)
    expect(items[0]).toHaveTextContent('Round 1 · challenge_slogan_01')
    expect(items[0]).toHaveTextContent('115 pts · correct')
    expect(items[1]).toHaveTextContent('missed')
  })

  it('handles an empty accuracy and offers a replay', async () => {
    render(
      <MemoryRouter>
        <SessionSummary summary={{ ...summary, accuracy: null, rounds: [] }} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('summary-accuracy')).toHaveTextContent('—')
    expect(
      screen.getByTestId('summary-rounds').querySelectorAll('li'),
    ).toHaveLength(0)
    expect(
      screen.getByRole('button', { name: /play again/i }),
    ).toBeInTheDocument()
  })
})
