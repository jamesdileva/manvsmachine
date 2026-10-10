import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { TOKEN_STORAGE_KEY, apiClient } from '@/api/client'
import { ScoringProvider } from '@/contexts/ScoringContext'
import { VotingProvider, useVotingContext } from '@/contexts/VotingContext'
import SessionPage from '@/pages/session'
import { useRoundState, useSessionEvents } from '@/websocket/hooks'
import { ServerEvent } from '@/websocket/events'
import type { SocketLike } from '@/websocket/client'

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
  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }
}

let socket: FakeSocket
let mock: MockAdapter

beforeEach(() => {
  socket = new FakeSocket()
  mock = new MockAdapter(apiClient)
  localStorage.clear()
  localStorage.setItem(TOKEN_STORAGE_KEY, 'a.b.c')
  mock.onPost('/session/start').reply(201, {
    session_id: 's1',
    type: 'daily',
    rounds_total: 3,
    next_challenge: {
      id: 'challenge_slogan_01',
      prompt: 'Write a slogan.',
      time_limit_seconds: 15,
    },
    round_id: 'r1',
  })
  mock.onGet('/challenges/challenge_slogan_01').reply(200, {
    id: 'challenge_slogan_01',
    name: 'Tiny Tagline',
    interactionType: 'Quick Text',
    prompt: 'Write a slogan for a dragon-owned bakery.',
    constraints: [{ type: 'max_words', value: 5, isHard: true }],
    timeLimitSeconds: 15,
    inputType: 'text_single_line',
    votingCriteria: 'most_believable',
    difficulty: 2,
    scoringRules: {
      baseScore: 100,
      timeBonusMultiplier: 0.15,
      streakMultiplier: 0.05,
    },
    aiPromptTemplateId: 'v1.0',
    aiPromptGuidance: '',
    replayability: { dailyVariants: 3, constraintPool: [] },
  })
})

/** The Session page plus probes for the new hooks. */
function Harness() {
  const round = useRoundState()
  const session = useSessionEvents()
  const voting = useVotingContext()
  return (
    <div>
      <span data-testid="phase">{round.phase}</span>
      <span data-testid="rounds-total">{session.roundsTotal}</span>
      <span data-testid="complete">{String(session.isComplete)}</span>
      <span data-testid="summary">{voting.summary?.total_score ?? '-'}</span>
    </div>
  )
}

function renderSession() {
  const factory = vi.fn(() => socket as unknown as WebSocket)
  const view = render(
    <MemoryRouter>
      <VotingProvider socketFactory={factory}>
        <ScoringProvider>
          <SessionPage />
          <Harness />
        </ScoringProvider>
      </VotingProvider>
    </MemoryRouter>,
  )
  return { ...view, factory }
}

/** Wait for the page to open its channel, then replay the round handshake. */
async function openRound(factory: ReturnType<typeof vi.fn>) {
  await vi.waitFor(() => expect(factory).toHaveBeenCalled())
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
}

describe('useRoundState / useSessionEvents', () => {
  it('starts idle and tracks the session shape', async () => {
    const { factory } = renderSession()
    expect(screen.getByTestId('phase')).toHaveTextContent('idle')
    expect(screen.getByTestId('complete')).toHaveTextContent('false')

    await openRound(factory)
    expect(screen.getByTestId('phase')).toHaveTextContent('writing')
    expect(screen.getByTestId('rounds-total')).toHaveTextContent('3')
  })
})

describe('Session page game loop', () => {
  it('plays a full round through the socket', async () => {
    const user = userEvent.setup()
    const { factory } = renderSession()

    await screen.findByRole('heading', { name: 'Session', level: 1 })
    await openRound(factory)
    expect(screen.getByTestId('phase')).toHaveTextContent('writing')

    // Submit the human entry; the AI pair arrives.
    await user.click(await screen.findByRole('button', { name: /submit/i }))
    await act(async () => {
      socket.emit({
        type: ServerEvent.AI_RESPONSE_READY,
        data: {
          roundId: 'r1',
          entries: {
            A: 'Bread baked by a dragon',
            B: 'Fire baked. Dragon approved.',
          },
        },
      })
    })
    expect(screen.getByTestId('phase')).toHaveTextContent('voting')
    expect(screen.getByTestId('entry-B')).toHaveTextContent(
      'Fire baked. Dragon approved.',
    )

    // Vote for the AI letter (B here).
    await user.click(screen.getByRole('button', { name: 'B is the AI' }))
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
          explanation: 'Entry B was the AI — nice catch.',
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
    })

    expect(screen.getByTestId('reveal-screen')).toBeInTheDocument()
    expect(screen.getByTestId('score-total')).toBeInTheDocument()
    expect(screen.getByTestId('phase')).toHaveTextContent('scored')

    // Finishing the session shows the summary.
    await act(async () => {
      socket.emit({
        type: ServerEvent.SESSION_END,
        data: {
          sessionId: 's1',
          summary: {
            session_id: 's1',
            type: 'daily',
            total_score: 115,
            accuracy: 100,
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
            ],
            rating_change: null,
            streak: 1,
          },
        },
      })
    })
    expect(screen.getByTestId('complete')).toHaveTextContent('true')
    expect(screen.getByTestId('summary')).toHaveTextContent('115')
    expect(screen.getByTestId('session-summary')).toBeInTheDocument()
  }, 30_000)
})
