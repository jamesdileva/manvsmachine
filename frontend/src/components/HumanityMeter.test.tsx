import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { HumanityMeter } from '@/components/HumanityMeter'

describe('HumanityMeter', () => {
  it('renders a 0-100 progressbar with the score', () => {
    render(<HumanityMeter score={68} />)

    const meter = screen.getByRole('progressbar', {
      name: 'Your entries humanity score',
    })
    expect(meter).toHaveAttribute('aria-valuenow', '68')
    expect(meter).toHaveAttribute('aria-valuemin', '0')
    expect(meter).toHaveAttribute('aria-valuemax', '100')
    expect(screen.getByTestId('humanity-value')).toHaveTextContent('68')
  })

  it('clamps out-of-range scores', () => {
    render(<HumanityMeter score={142} />)
    expect(
      screen.getByRole('progressbar', { name: 'Your entries humanity score' }),
    ).toHaveAttribute('aria-valuenow', '100')

    render(<HumanityMeter score={-12} />)
    const meters = screen.getAllByRole('progressbar')
    expect(meters[meters.length - 1]).toHaveAttribute('aria-valuenow', '0')
  })

  it('accepts a custom label', () => {
    render(<HumanityMeter score={50} label="challenge_slogan_01" />)
    expect(
      screen.getByRole('progressbar', {
        name: 'challenge_slogan_01 humanity score',
      }),
    ).toBeInTheDocument()
  })
})
