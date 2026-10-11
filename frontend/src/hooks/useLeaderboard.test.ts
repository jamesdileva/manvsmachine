import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { apiClient } from '@/api/client'
import { useLeaderboard } from '@/hooks/useLeaderboard'

let mock: MockAdapter

const dailyResponse = {
  date: '2026-10-10',
  entries: [
    {
      rank: 1,
      user_id: 'u1',
      display_name: 'Alex',
      score: 300,
      rating: null,
      accuracy: 100,
    },
    {
      rank: 2,
      user_id: 'u2',
      display_name: 'Jordan',
      score: 275,
      rating: null,
      accuracy: 66.7,
    },
  ],
}

const allTimeResponse = {
  entries: [
    {
      rank: 1,
      user_id: 'u3',
      display_name: 'Morgan',
      score: null,
      rating: 1450,
      accuracy: 71.4,
    },
    {
      rank: 2,
      user_id: 'u4',
      display_name: 'Sam',
      score: null,
      rating: 1380,
      accuracy: 60.0,
    },
  ],
}

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})

describe('useLeaderboard', () => {
  it('loads the daily board', async () => {
    mock.onGet('/leaderboard/daily').reply(200, dailyResponse)

    const { result } = renderHook(() => useLeaderboard())
    await act(async () => {
      await result.current.loadDaily()
    })

    expect(result.current.daily?.date).toBe('2026-10-10')
    expect(result.current.daily?.entries).toHaveLength(2)
    expect(result.current.error).toBeNull()
    expect(result.current.isLoading).toBe(false)
  })

  it('loads the all-time board', async () => {
    mock.onGet('/leaderboard/all-time').reply(200, allTimeResponse)

    const { result } = renderHook(() => useLeaderboard())
    await act(async () => {
      await result.current.loadAllTime()
    })

    expect(result.current.allTime?.entries[0].rating).toBe(1450)
    expect(result.current.daily).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('surfaces errors from the daily lookup', async () => {
    mock.onGet('/leaderboard/daily').reply(500, { detail: 'boom' })

    const { result } = renderHook(() => useLeaderboard())
    await act(async () => {
      await result.current.loadDaily()
    })

    expect(result.current.error).toBe('boom')
    expect(result.current.daily).toBeNull()
    expect(result.current.isLoading).toBe(false)
  })
})
