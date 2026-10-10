import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { VotingScreen } from '@/components/VotingScreen'

const entries = {
  A: 'Fire baked. Dragon approved.',
  B: "Dragon's fire, fresh baked.",
}

describe('VotingScreen', () => {
  it('shows both entries labeled A and B with no origin hints', () => {
    render(<VotingScreen entries={entries} onVote={vi.fn()} />)

    expect(screen.getByTestId('entry-A')).toHaveTextContent(
      'Fire baked. Dragon approved.',
    )
    expect(screen.getByTestId('entry-B')).toHaveTextContent(
      "Dragon's fire, fresh baked.",
    )
    expect(screen.getByText('Entry A')).toBeInTheDocument()
    expect(screen.getByText('Entry B')).toBeInTheDocument()
    // Nothing reveals which entry is the player's.
    expect(screen.queryByText(/yours/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/you wrote/i)).not.toBeInTheDocument()
  })

  it('submits a vote for the chosen letter', async () => {
    const user = userEvent.setup()
    const onVote = vi.fn()
    render(<VotingScreen entries={entries} onVote={onVote} />)

    await user.click(screen.getByRole('button', { name: 'A is the AI' }))
    expect(onVote).toHaveBeenCalledWith('A')

    await user.click(screen.getByRole('button', { name: 'B is the AI' }))
    expect(onVote).toHaveBeenCalledWith('B')
  })

  it('shows a loading state while waiting for the AI entry', () => {
    render(<VotingScreen entries={null} onVote={vi.fn()} />)
    expect(screen.getByText(/waiting for the other entry/i)).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /is the AI/ }),
    ).not.toBeInTheDocument()
  })

  it('disables the vote buttons after voting', () => {
    render(<VotingScreen entries={entries} onVote={vi.fn()} disabled />)
    expect(screen.getByRole('button', { name: 'A is the AI' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'B is the AI' })).toBeDisabled()
  })

  it('nudges after the voting window expires without locking the buttons', async () => {
    vi.useFakeTimers()
    try {
      render(<VotingScreen entries={entries} onVote={vi.fn()} />)
      expect(screen.queryByTestId('voting-nudge')).not.toBeInTheDocument()

      await act(async () => {
        await vi.advanceTimersByTimeAsync(10_000)
      })
      expect(screen.getByTestId('voting-nudge')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'A is the AI' })).toBeEnabled()
    } finally {
      vi.useRealTimers()
    }
  })
})
