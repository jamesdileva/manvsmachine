import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { apiClient } from '@/api/client'
import { useChallenges } from '@/hooks/useChallenges'
import type { ChallengeDefinition, ValidateResponse } from '@/types'

let mock: MockAdapter

const dailyResponse = {
  challenge: {
    id: 'challenge_slogan_01',
    name: 'Tiny Tagline',
    prompt: 'Write a slogan for a dragon-owned bakery.',
    constraints: [{ type: 'max_words', value: 5, isHard: true }],
    time_limit_seconds: 15,
    input_type: 'text_single_line',
    voting_criteria: 'most_believable',
    difficulty: 2,
  },
  session_id: 's1',
  round_number: 1,
  round_id: 'r1',
}

const definition = {
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
}

beforeEach(() => {
  mock = new MockAdapter(apiClient)
  localStorage.clear()
})

describe('useChallenges', () => {
  it('loads the daily challenge and its full definition', async () => {
    mock
      .onGet('/challenges/daily')
      .reply(200, dailyResponse)
      .onGet('/challenges/challenge_slogan_01')
      .reply(200, definition)

    const { result } = renderHook(() => useChallenges())
    await act(async () => {
      await result.current.loadDaily()
    })

    expect(result.current.daily?.round_id).toBe('r1')
    expect(result.current.challenge?.timeLimitSeconds).toBe(15)
    expect(result.current.error).toBeNull()
    expect(result.current.isLoading).toBe(false)
  })

  it('surfaces errors from the daily lookup', async () => {
    mock.onGet('/challenges/daily').reply(500, { detail: 'boom' })
    const { result } = renderHook(() => useChallenges())

    await act(async () => {
      await result.current.loadDaily()
    })
    expect(result.current.error).toBe('boom')
    expect(result.current.challenge).toBeNull()
    expect(result.current.isLoading).toBe(false)
  })

  it('loads a challenge by id', async () => {
    mock
      .onGet('/challenges/challenge_emoji_03')
      .reply(200, { ...definition, id: 'challenge_emoji_03' })
    const { result } = renderHook(() => useChallenges())
    const holder: { loaded: ChallengeDefinition | null } = { loaded: null }

    await act(async () => {
      holder.loaded = await result.current.loadChallenge('challenge_emoji_03')
    })
    expect(holder.loaded?.id).toBe('challenge_emoji_03')
    expect(result.current.challenge?.id).toBe('challenge_emoji_03')
  })

  it('validates entries server-side', async () => {
    mock.onPost('/challenges/validate').reply(200, {
      valid: false,
      hard_violations: ['too many words (6 > 5)'],
      soft_violations: [],
      word_count: 6,
      character_count: 40,
    })
    const { result } = renderHook(() => useChallenges())
    const holder: { validation: ValidateResponse | null } = { validation: null }

    await act(async () => {
      holder.validation = await result.current.validateEntry(
        'challenge_slogan_01',
        'one two three four five six',
      )
    })
    expect(holder.validation?.valid).toBe(false)
    expect(holder.validation?.word_count).toBe(6)
  })
})
