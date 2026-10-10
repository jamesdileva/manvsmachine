import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ScoreAnimation } from '@/components/ScoreAnimation'
import type { RoundScore } from '@/types'

const score: RoundScore = {
  vote_correct: true,
  base: 100,
  time_bonus: 15,
  streak_bonus: 10,
  total: 125,
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('ScoreAnimation', () => {
  it('counts up to the total', () => {
    render(<ScoreAnimation score={score} />)
    expect(screen.getByTestId('score-total')).toHaveTextContent('0')

    act(() => {
      vi.advanceTimersByTime(400)
    })
    const midway = Number(screen.getByTestId('score-total').textContent)
    expect(midway).toBeGreaterThan(0)
    expect(midway).toBeLessThan(125)

    act(() => {
      vi.advanceTimersByTime(500)
    })
    expect(screen.getByTestId('score-total')).toHaveTextContent('125')
  })

  it('shows the score breakdown', () => {
    render(<ScoreAnimation score={score} duration={0} />)
    expect(screen.getByText('Correct detection')).toBeInTheDocument()
    expect(screen.getByText('Speed bonus')).toBeInTheDocument()
    expect(screen.getByText('Streak bonus')).toBeInTheDocument()
    expect(screen.getByTestId('score-breakdown-total')).toHaveTextContent('125')
  })

  it('labels a missed detection', () => {
    render(
      <ScoreAnimation
        score={{ ...score, vote_correct: false, base: 0, total: 25 }}
        duration={0}
      />,
    )
    expect(screen.getByText('Detection missed')).toBeInTheDocument()
    expect(screen.getByTestId('score-total')).toHaveTextContent('25')
  })
})
