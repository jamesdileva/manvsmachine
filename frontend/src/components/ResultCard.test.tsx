import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { apiClient } from '@/api/client'
import { ResultCard } from '@/components/ResultCard'
import type { SessionSummaryResponse } from '@/types'

let mock: MockAdapter

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

function renderCard() {
  return render(
    <MemoryRouter>
      <ResultCard summary={summary} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})

describe('ResultCard', () => {
  it('shows the score and accuracy', () => {
    renderCard()
    expect(screen.getByTestId('result-total')).toHaveTextContent('345')
    expect(screen.getByTestId('result-accuracy')).toHaveTextContent('67%')
  })

  it('averages the humanity scores across the rounds', () => {
    renderCard()
    expect(screen.getByTestId('result-humanity-human')).toHaveTextContent('67')
    expect(screen.getByTestId('result-humanity-ai')).toHaveTextContent('33')
  })

  it('carries the share button for the session', () => {
    renderCard()
    expect(screen.getByRole('button', { name: /share/i })).toBeInTheDocument()
    expect(mock.history.post).toHaveLength(0) // nothing fetched until shared
  })
})
