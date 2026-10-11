import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
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
      time_limit_seconds: 1,
    },
    round_id: 'r1',
  })
  mock.onGet('/challenges/challenge_slogan_01').reply(200, {
    id: 'challenge_slogan_01',
    name: 'Tiny Tagline',
    interactionType: 'Quick Text',
    prompt: 'p',
    constraints: [],
    timeLimitSeconds: 1,
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
  mock
    .onGet('/auth/me')
    .reply(200, { user_id: 'u1', display_name: 'Alex', is_guest: false })
})

afterEach(() => {
  cleanup()
  mock.restore()
})

function renderSession() {
  const factory = vi.fn(() => socket as unknown as WebSocket)
  const view = renderHook(() => useSessionContext(), {
    wrapper: ({ children }) => (
      <VotingProvider socketFactory={factory}>
        <ScoringProvider>
          <SessionProvider scoreDwellMs={0}>{children}</SessionProvider>
        </ScoringProvider>
      </VotingProvider>
    ),
  })
  return { ...view, factory }
}

/** The round clock auto-submits the player's entry when it runs out. */
describe('SessionContext clock', () => {
  it('auto-submits the entry when the clock expires', async () => {
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
            time_limit_seconds: 1,
          },
          timeLimitSeconds: 1,
          state: 'writing',
        },
      })
    })
    expect(result.current.gameState).toBe('writing')

    act(() => result.current.setEntry(HUMAN_ENTRY))
    await waitFor(() => expect(socket.sent).toHaveLength(1), {
      timeout: 5_000,
      interval: 50,
    })
    expect(JSON.parse(socket.sent[0])).toEqual({
      type: 'SUBMIT_ENTRY',
      data: { roundId: 'r1', entry: HUMAN_ENTRY, sessionId: undefined },
    })
  }, 30_000)
})

describe('useSession guard', () => {
  it('throws outside the SessionProvider', () => {
    expect(() => renderHook(() => useSessionContext())).toThrow(
      /SessionProvider/,
    )
  })
})
