import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RatingDisplay } from '@/components/RatingDisplay'
import { StreakBadge } from '@/components/StreakBadge'

describe('StreakBadge', () => {
  it('shows the streak length', () => {
    render(<StreakBadge days={5} />)
    expect(screen.getByTestId('streak-badge')).toHaveTextContent('5-day streak')
  })
})

describe('RatingDisplay', () => {
  it('shows the rating rounded', () => {
    render(<RatingDisplay rating={1012.4} />)
    expect(screen.getByTestId('rating-display')).toHaveTextContent('1,012')
  })

  it('shows gains, losses, and no-change', () => {
    const { rerender } = render(<RatingDisplay rating={1007.7} change={7.7} />)
    expect(screen.getByTestId('rating-change')).toHaveTextContent('8')
    expect(screen.getByTestId('rating-change')).toHaveClass('text-green-600')

    rerender(<RatingDisplay rating={992.3} change={-7.7} />)
    expect(screen.getByTestId('rating-change')).toHaveClass('text-destructive')

    rerender(<RatingDisplay rating={1000} change={0} />)
    expect(screen.getByTestId('rating-change')).toHaveTextContent('±0')
  })
})
