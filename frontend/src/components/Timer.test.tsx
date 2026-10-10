import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Timer } from '@/components/Timer'

describe('Timer', () => {
  it('shows the remaining seconds and progress', () => {
    render(<Timer secondsLeft={10} totalSeconds={15} />)
    expect(screen.getByTestId('timer-seconds')).toHaveTextContent('10')
    const bar = screen.getByRole('progressbar', { name: 'Time remaining' })
    expect(bar).toHaveAttribute('aria-valuenow', '10')
    expect(bar).toHaveAttribute('aria-valuemax', '15')
  })

  it('turns red inside the last five seconds', () => {
    render(<Timer secondsLeft={5} totalSeconds={15} />)
    expect(screen.getByTestId('timer-seconds')).toHaveClass('text-destructive')
  })

  it('warns in the last ten seconds but not red', () => {
    render(<Timer secondsLeft={8} totalSeconds={15} />)
    expect(screen.getByTestId('timer-seconds')).not.toHaveClass(
      'text-destructive',
    )
  })

  it('shows the time-up marker when stopped at zero', () => {
    render(<Timer secondsLeft={0} totalSeconds={15} isRunning={false} />)
    expect(screen.getByText('Time!')).toBeInTheDocument()
  })
})
