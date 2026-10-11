import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { TOKEN_STORAGE_KEY, apiClient } from '@/api/client'
import { ScoringProvider } from '@/contexts/ScoringContext'
import { SessionProvider, useSessionContext } from '@/contexts/SessionContext'
import { VotingProvider } from '@/contexts/VotingContext'
import { ServerEvent } from '@/websocket/events'
import type { SocketLike } from '@/websocket/client'

const HUMAN_ENTRY = 'Bread baked by a dragon'

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

const CHALLENGE_DEFINITION = {
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
}

beforeEach(() => {
  vi.useFakeTimers({
    toFake: [
      'setTimeout',
      'setInterval',
      'clearTimeout',
      'clearInterval',
      'Date',
    ],
  })
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
  mock.onGet('/challenges/challenge_slogan_01').reply(200, CHALLENGE_DEFINITION)
  mock
    .onGet('/auth/me')
    .reply(200, { user_id: 'u1', display_name: 'Alex', is_guest: false })
})

afterEach(() => {
  cleanup()
  mock.restore()
  vi.useRealTimers()
})

function renderSession() {
  const factory = vi.fn(() => socket as unknown as WebSocket)
  return renderHook(() => useSessionContext(), {
    wrapper: ({ children }) => (
      <VotingProvider socketFactory={factory}>
        <ScoringProvider>
          <SessionProvider scoreDwellMs={0}>{children}</SessionProvider>
        </ScoringProvider>
      </VotingProvider>
    ),
  })
}

describe('SessionContext bisect', () => {
  it('reaches reveal_ai', async () => {
    const { result } = renderSession()
    await act(async () => {
      await result.current.startSession()
    })
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
            prompt: 'p',
            time_limit_seconds: 15,
          },
          timeLimitSeconds: 15,
          state: 'writing',
        },
      })
    })

    act(() => result.current.submitEntry(HUMAN_ENTRY))
    await act(async () => {
      socket.emit({
        type: ServerEvent.AI_RESPONSE_READY,
        data: { roundId: 'r1', entries: { A: HUMAN_ENTRY, B: 'Fire baked.' } },
      })
    })

    act(() => result.current.submitVote('B'))
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
    })
    expect(result.current.gameState).toBe('reveal_ai')

    await act(async () => {
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
    expect(result.current.gameState).toBe('score')

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
            rounds: [],
            rating_change: null,
            streak: 1,
          },
        },
      })
    })
    await act(async () => {
      vi.advanceTimersByTime(10)
    })
    expect(result.current.gameState).toBe('complete')
  }, 15_000)
})
