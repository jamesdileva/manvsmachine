import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TOKEN_STORAGE_KEY } from '@/api/client'
import { ScoringProvider, useScoringContext } from '@/contexts/ScoringContext'
import { VotingProvider, useVotingContext } from '@/contexts/VotingContext'
import { type SocketLike } from '@/websocket/client'
import { ServerEvent } from '@/websocket/events'

class FakeSocket implements SocketLike {
  sent: string[] = []
  closed = false
  onopen: ((event: unknown) => void) | null = null
  onmessage: ((event: { data: unknown }) => void) | null = null
  onclose: ((event: { code: number; reason?: string }) => void) | null = null
  onerror: ((event: unknown) => void) | null = null

  send(data: string): void {
    this.sent.push(data)
  }
  close(): void {
    this.closed = true
  }

  open() {
    this.onopen?.({})
  }
  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }
}

let socket: FakeSocket

function harness() {
  const factory = vi.fn(() => socket as unknown as WebSocket)
  const view = render(
    <VotingProvider socketFactory={factory}>
      <ScoringProvider>
        <Probe />
      </ScoringProvider>
    </VotingProvider>,
  )
  return { ...view, factory }
}

function Probe() {
  const voting = useVotingContext()
  const scoring = useScoringContext()
  return (
    <div>
      <span data-testid="status">{voting.status}</span>
      <span data-testid="entries">{JSON.stringify(voting.entries)}</span>
      <span data-testid="round">{voting.round?.roundNumber ?? '-'}</span>
      <span data-testid="reveal">
        {String(voting.reveal?.voteCorrect ?? '-')}
      </span>
      <span data-testid="score">{scoring.score?.score.total ?? '-'}</span>
      <span data-testid="rating-change">{scoring.ratingChange}</span>
      <span data-testid="summary">{scoring.summary?.total_score ?? '-'}</span>
      <span data-testid="error">{voting.error ?? '-'}</span>
      <button onClick={() => voting.connect('s1')}>connect</button>
      <button onClick={() => voting.vote('r1', 'A')}>vote</button>
      <button onClick={() => voting.submitEntry('r1', 'Fire baked.')}>
        submit
      </button>
    </div>
  )
}

beforeEach(() => {
  socket = new FakeSocket()
  localStorage.clear()
  localStorage.setItem(TOKEN_STORAGE_KEY, 'a.b.c')
})

describe('VotingContext + ScoringContext', () => {
  it('connects and tracks the session lifecycle', async () => {
    const user = userEvent.setup()
    const { factory } = harness()

    await user.click(screen.getByRole('button', { name: 'connect' }))
    expect(factory).toHaveBeenCalledWith(
      expect.stringContaining('/ws/session/s1?token=a.b.c'),
    )
    expect(screen.getByTestId('status')).toHaveTextContent('connecting')

    await act(async () => {
      socket.open()
    })
    expect(screen.getByTestId('status')).toHaveTextContent('open')

    // SESSION_STARTED then ROUND_START resets the round view.
    await act(async () => {
      socket.emit({
        type: ServerEvent.SESSION_STARTED,
        data: {
          sessionId: 's1',
          rounds: 3,
          roundsPlayed: 0,
          completed: false,
          challenges: [],
        },
      })
    })
    await act(async () => {
      socket.emit({
        type: ServerEvent.ROUND_START,
        data: {
          roundId: 'r1',
          roundNumber: 1,
          roundsTotal: 3,
          challenge: {
            id: 'challenge_slogan_01',
            prompt: 'Write a slogan.',
            time_limit_seconds: 15,
          },
          timeLimitSeconds: 15,
          state: 'writing',
        },
      })
    })
    expect(screen.getByTestId('round')).toHaveTextContent('1')
    expect(screen.getByTestId('entries')).toHaveTextContent('null')

    // AI_RESPONSE_READY fills the anonymized entries.
    await act(async () => {
      socket.emit({
        type: ServerEvent.AI_RESPONSE_READY,
        data: {
          roundId: 'r1',
          entries: { A: 'Fire baked.', B: "Dragon's fire." },
        },
      })
    })
    expect(screen.getByTestId('entries')).toHaveTextContent('Fire baked.')
  })

  it('sends the vote for the chosen letter', async () => {
    const user = userEvent.setup()
    harness()
    await user.click(screen.getByRole('button', { name: 'connect' }))

    await user.click(screen.getByRole('button', { name: 'vote' }))
    expect(JSON.parse(socket.sent[0])).toEqual({
      type: 'VOTE',
      data: { roundId: 'r1', vote: 'A', sessionId: undefined },
    })
  })

  it('routes reveal/score/session-end events into state', async () => {
    const user = userEvent.setup()
    harness()
    await user.click(screen.getByRole('button', { name: 'connect' }))

    await act(async () => {
      socket.emit({
        type: ServerEvent.REVEAL,
        data: {
          roundId: 'r1',
          humanWas: 'A',
          aiWas: 'B',
          vote: 'B',
          voteCorrect: true,
          humanityHuman: 100,
          humanityAI: 0,
          explanation: 'Entry B was the AI.',
        },
      })
      socket.emit({
        type: ServerEvent.ROUND_SCORED,
        data: {
          roundId: 'r1',
          score: {
            vote_correct: true,
            base: 100,
            time_bonus: 15,
            streak_bonus: 0,
            total: 115,
          },
          ratingChange: 7.7,
          streakUpdate: 1,
        },
      })
      socket.emit({
        type: ServerEvent.SESSION_END,
        data: {
          sessionId: 's1',
          summary: { session_id: 's1', total_score: 345 },
        },
      })
    })

    expect(screen.getByTestId('reveal')).toHaveTextContent('true')
    expect(screen.getByTestId('score')).toHaveTextContent('115')
    expect(screen.getByTestId('rating-change')).toHaveTextContent('7.7')
    expect(screen.getByTestId('summary')).toHaveTextContent('345')
  })

  it('surfaces server errors', async () => {
    const user = userEvent.setup()
    harness()
    await user.click(screen.getByRole('button', { name: 'connect' }))

    await act(async () => {
      socket.emit({
        type: ServerEvent.ERROR,
        data: { code: 'ConflictError', message: 'round already revealed' },
      })
    })
    expect(screen.getByTestId('error')).toHaveTextContent(
      'round already revealed',
    )
  })
})

describe('useVoting outside the provider', () => {
  it('throws a helpful error', () => {
    expect(() => render(<Probe />)).toThrow(/VotingProvider/)
  })
})
