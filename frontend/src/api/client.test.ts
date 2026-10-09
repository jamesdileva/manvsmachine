import { beforeEach, describe, expect, it } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { TOKEN_STORAGE_KEY, apiClient } from '@/api/client'
import { toApiError } from '@/api/errors'
import { authApi } from '@/api/auth'
import { challengesApi } from '@/api/challenges'
import { leaderboardApi } from '@/api/leaderboard'
import { profileApi } from '@/api/profile'
import { sessionApi } from '@/api/session'
import { shareApi } from '@/api/share'
import { votingApi } from '@/api/voting'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
  localStorage.clear()
})

const TOKEN = 'header.payload.signature'

describe('auth api', () => {
  it('creates a guest session', async () => {
    const response = {
      user_id: 'u1',
      guest_id: 'g1',
      display_name: 'Player_1234',
      is_guest: true,
      token: TOKEN,
    }
    mock.onPost('/auth/guest').reply(201, response)

    const result = await authApi.guest()
    expect(result.token).toBe(TOKEN)
    expect(result.is_guest).toBe(true)
  })

  it('sends resume credentials when provided', async () => {
    mock
      .onPost('/auth/guest', { guest_id: 'g9', display_name: 'Returning' })
      .reply(201, {
        user_id: 'u9',
        guest_id: 'g9',
        display_name: 'Returning',
        is_guest: true,
        token: TOKEN,
      })

    const result = await authApi.guest({
      guest_id: 'g9',
      display_name: 'Returning',
    })
    expect(result.guest_id).toBe('g9')
  })

  it('registers and logs in', async () => {
    mock
      .onPost('/auth/register')
      .reply(201, {
        user_id: 'u2',
        display_name: 'Alex',
        is_guest: false,
        token: TOKEN,
      })
      .onPost('/auth/login')
      .reply(200, {
        user_id: 'u2',
        display_name: 'Alex',
        is_guest: false,
        token: TOKEN,
      })

    const registered = await authApi.register({
      email: 'alex@example.com',
      password: 'password123',
      display_name: 'Alex',
    })
    expect(registered.is_guest).toBe(false)

    const loggedIn = await authApi.login({
      email: 'alex@example.com',
      password: 'password123',
    })
    expect(loggedIn.token).toBe(TOKEN)
  })

  it('fetches the current user', async () => {
    mock
      .onGet('/auth/me')
      .reply(200, { user_id: 'u1', display_name: 'Player_1', is_guest: true })
    const me = await authApi.me()
    expect(me.user_id).toBe('u1')
  })
})

describe('challenges api', () => {
  it('fetches the daily challenge', async () => {
    mock.onGet('/challenges/daily').reply(200, {
      challenge: { id: 'challenge_slogan_01' },
      session_id: 's1',
      round_number: 1,
    })
    const daily = await challengesApi.daily()
    expect(daily.session_id).toBe('s1')
  })

  it('passes the optional player rating', async () => {
    mock
      .onGet('/challenges/daily', { params: { player_rating: 1250 } })
      .reply(200, {
        challenge: { id: 'challenge_slogan_01' },
        session_id: 's1',
        round_number: 1,
      })
    const daily = await challengesApi.daily(1250)
    expect(daily.session_id).toBe('s1')
  })

  it('fetches a full definition and validates entries', async () => {
    mock
      .onGet('/challenges/challenge_slogan_01')
      .reply(200, {
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
        aiPromptGuidance: 'Be casual.',
        replayability: { dailyVariants: 3, constraintPool: [] },
      })
      .onPost('/challenges/validate')
      .reply(200, {
        valid: true,
        hard_violations: [],
        soft_violations: [],
        word_count: 4,
        character_count: 28,
      })

    const challenge = await challengesApi.byId('challenge_slogan_01')
    expect(challenge.timeLimitSeconds).toBe(15)
    expect(challenge.constraints[0].isHard).toBe(true)

    const validation = await challengesApi.validate({
      challenge_id: 'challenge_slogan_01',
      entry: 'Fire baked. Dragon approved.',
    })
    expect(validation.word_count).toBe(4)
  })
})

describe('session api', () => {
  it('starts a session and reads its state', async () => {
    mock
      .onPost('/session/start')
      .reply(201, {
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
      .onGet('/session/s1')
      .reply(200, {
        session_id: 's1',
        type: 'daily',
        current_round: 1,
        rounds_total: 3,
        state: 'in_progress',
        started_at: '2026-10-08T00:00:00Z',
        completed_at: null,
      })

    const started = await sessionApi.start({ type: 'daily' })
    expect(started.round_id).toBe('r1')

    const state = await sessionApi.state('s1')
    expect(state.current_round).toBe(1)
  })

  it('submits a round entry and fetches the summary', async () => {
    mock
      .onPost('/session/s1/rounds/r1/entry')
      .reply(200, {
        round_id: 'r1',
        entries: {
          A: 'Fire baked. Dragon approved.',
          B: "Dragon's fire, fresh baked.",
        },
        ai_provider: 'ollama',
        ai_model: 'qwen3.5:9b',
        hard_violations: [],
        soft_violations: [],
      })
      .onGet('/session/s1/summary')
      .reply(200, {
        session_id: 's1',
        type: 'daily',
        total_score: 275,
        accuracy: 66.7,
        rounds: [],
        rating_change: null,
        streak: 2,
      })

    const submission = await sessionApi.submitEntry(
      's1',
      'r1',
      'Fire baked. Dragon approved.',
    )
    expect(submission.entries.A).toBe('Fire baked. Dragon approved.')

    const summary = await sessionApi.summary('s1')
    expect(summary.total_score).toBe(275)
  })

  it('advances to the next round', async () => {
    mock.onPost('/session/s1/next').reply(200, {
      complete: false,
      round: {
        round_id: 'r2',
        challenge: {
          id: 'challenge_emoji_03',
          prompt: 'Tell a movie plot.',
          time_limit_seconds: 20,
        },
        round_number: 2,
        rounds_total: 3,
        state: 'writing',
      },
    })
    const next = await sessionApi.next('s1')
    expect(next.round?.round_number).toBe(2)
    expect(next.complete).toBe(false)
  })
})

describe('voting api', () => {
  it('submits a practice entry', async () => {
    mock.onPost('/voting/submit-entry').reply(200, {
      challenge_id: 'challenge_slogan_01',
      human_entry: 'Fire baked. Dragon approved.',
      ai_entry: "Dragon's fire, fresh baked.",
      provider: 'ollama',
      model: 'qwen3.5:9b',
      hard_violations: [],
      soft_violations: [],
    })
    const result = await votingApi.submitEntry({
      challenge_id: 'challenge_slogan_01',
      entry: 'Fire baked. Dragon approved.',
    })
    expect(result.ai_entry).toBeTruthy()
  })

  it('votes and returns the reveal with the score', async () => {
    mock.onPost('/voting/vote').reply(200, {
      round_id: 'r1',
      entries: {
        A: 'Fire baked. Dragon approved.',
        B: "Dragon's fire, fresh baked.",
      },
      human_was: 'A',
      ai_was: 'B',
      vote: 'B',
      vote_correct: true,
      humanity_human: 100,
      humanity_ai: 0,
      explanation: 'Entry B was the AI — nice catch.',
      base: 100,
      time_bonus: 15,
      streak_bonus: 0,
      total: 115,
      detection_rating: 1007.7,
      streak: 1,
    })
    const result = await votingApi.vote({ round_id: 'r1', vote: 'B' })
    expect(result.vote_correct).toBe(true)
    expect(result.total).toBe(115)
    expect(result.detection_rating).toBeGreaterThan(1000)
  })
})

describe('leaderboard api', () => {
  it('fetches the daily and all-time boards', async () => {
    mock
      .onGet('/leaderboard/daily')
      .reply(200, {
        date: '2026-10-08',
        entries: [
          {
            rank: 1,
            user_id: 'u1',
            display_name: 'Alex',
            score: 300,
            accuracy: 100,
          },
        ],
      })
      .onGet('/leaderboard/all-time')
      .reply(200, {
        entries: [
          {
            rank: 1,
            user_id: 'u1',
            display_name: 'Morgan',
            rating: 1450,
            score: null,
            accuracy: 82.5,
          },
        ],
      })

    const daily = await leaderboardApi.daily()
    expect(daily.entries[0].score).toBe(300)

    const allTime = await leaderboardApi.allTime()
    expect(allTime.entries[0].rating).toBe(1450)
  })
})

describe('profile and share api', () => {
  it('calls the profile endpoints', async () => {
    mock
      .onGet('/profile')
      .reply(200, {
        user_id: 'u1',
        display_name: 'Alex',
        is_guest: false,
        detection_rating: 1012,
        total_rounds: 47,
        overall_accuracy: 62.3,
        current_streak: 3,
        longest_streak: 7,
        daily_challenge_streak: 5,
        recent_humanity_scores: [
          {
            challenge_id: 'challenge_slogan_01',
            score: 68,
            date: '2026-10-01',
          },
        ],
      })
      .onPut('/profile')
      .reply(200, { user_id: 'u1', display_name: 'NewName' })

    const profile = await profileApi.get()
    expect(profile.detection_rating).toBe(1012)

    const updated = await profileApi.update({ display_name: 'NewName' })
    expect(updated.display_name).toBe('NewName')
  })

  it('calls the share endpoint', async () => {
    mock.onPost('/share/result').reply(200, {
      share_text: 'I scored 275!',
      share_url: '/s/abc123',
    })
    const share = await shareApi.result({ session_id: 's1' })
    expect(share.share_url).toBe('/s/abc123')
  })
})

describe('client interceptors', () => {
  it('attaches the stored token to requests', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, TOKEN)
    mock.onGet('/auth/me').reply((config) => {
      expect(config.headers?.Authorization).toBe(`Bearer ${TOKEN}`)
      return [200, { user_id: 'u1', display_name: 'Alex', is_guest: false }]
    })

    await authApi.me()
  })

  it('evicts the token on a 401', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, TOKEN)
    mock.onGet('/auth/me').reply(401, { detail: 'invalid token' })

    await expect(authApi.me()).rejects.toThrow()
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('keeps the token on other error statuses', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, TOKEN)
    mock.onGet('/auth/me').reply(500, { detail: 'boom' })

    await expect(authApi.me()).rejects.toThrow()
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe(TOKEN)
  })
})

describe('toApiError', () => {
  it('maps string detail payloads', () => {
    const error = toApiError({
      isAxiosError: true,
      message: 'Request failed with status code 404',
      response: { status: 404, data: { detail: 'session not found' } },
    })
    expect(error).toEqual({
      status: 404,
      message: 'session not found',
      details: 'session not found',
    })
  })

  it('maps violation objects into a readable message', () => {
    const error = toApiError({
      isAxiosError: true,
      message: 'Request failed with status code 400',
      response: {
        status: 400,
        data: { detail: { hard_violations: ['too many words (6 > 5)'] } },
      },
    })
    expect(error.status).toBe(400)
    expect(error.message).toContain('too many words')
  })

  it('maps unknown objects and plain errors', () => {
    expect(
      toApiError({ isAxiosError: true, message: 'Network Error' }),
    ).toEqual({
      status: 0,
      message: 'Network Error',
      details: undefined,
    })
    expect(toApiError(new Error('boom'))).toEqual({
      status: 0,
      message: 'boom',
      details: undefined,
    })
    expect(toApiError(null).message).toBe('Unexpected error')
  })
})
