import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RevealScreen } from '@/components/RevealScreen'
import type { RevealPayload } from '@/websocket/events'

const reveal: RevealPayload = {
  roundId: 'r1',
  humanWas: 'A',
  aiWas: 'B',
  vote: 'B',
  voteCorrect: true,
  humanityHuman: 100,
  humanityAI: 0,
  explanation:
    'Entry B was the AI — nice catch. Humanity: your entry 100, AI entry 0.',
  entries: {
    A: 'Fire baked. Dragon approved.',
    B: "Dragon's fire, fresh baked.",
  },
}

describe('RevealScreen', () => {
  it('shows the attribution and the player outcome', () => {
    render(<RevealScreen reveal={reveal} />)
    expect(
      screen.getByText(/Entry A was human · Entry B was the AI/),
    ).toBeInTheDocument()
    expect(screen.getByText('Correct')).toBeInTheDocument()
    expect(screen.getByTestId('revealed-entry-A')).toHaveTextContent('yours')
    expect(screen.getByTestId('revealed-entry-B')).toHaveTextContent('the AI')
  })

  it('renders humanity scores as 0-100 bars', () => {
    render(<RevealScreen reveal={reveal} />)
    const yours = screen.getByRole('progressbar', {
      name: 'Your entry humanity score',
    })
    const ai = screen.getByRole('progressbar', {
      name: 'AI entry humanity score',
    })
    expect(yours).toHaveAttribute('aria-valuenow', '100')
    expect(ai).toHaveAttribute('aria-valuenow', '0')
    expect(screen.getByTestId('humanity-your entry')).toHaveTextContent('100')
    expect(screen.getByTestId('humanity-ai entry')).toHaveTextContent('0')
  })

  it('shows a fooled outcome and the explanation', () => {
    render(
      <RevealScreen
        reveal={{
          ...reveal,
          vote: 'A',
          voteCorrect: false,
          humanityHuman: 0,
          humanityAI: 100,
        }}
      />,
    )
    expect(screen.getByText('Fooled')).toBeInTheDocument()
    expect(screen.getByTestId('reveal-explanation')).toHaveTextContent(
      /nice catch/,
    )
  })

  it('clamps out-of-range humanity values', () => {
    render(
      <RevealScreen
        reveal={{ ...reveal, humanityHuman: 150, humanityAI: -5 }}
      />,
    )
    expect(
      screen.getByRole('progressbar', { name: 'Your entry humanity score' }),
    ).toHaveAttribute('aria-valuenow', '100')
    expect(
      screen.getByRole('progressbar', { name: 'AI entry humanity score' }),
    ).toHaveAttribute('aria-valuenow', '0')
  })
})
