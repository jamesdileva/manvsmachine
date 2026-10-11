/** useLeaderboard: daily and all-time boards (Implementation Guide §2.4). */

import { useCallback, useState } from 'react'

import { leaderboardApi } from '@/api/leaderboard'
import { toApiError } from '@/api/errors'
import type {
  AllTimeLeaderboardResponse,
  DailyLeaderboardResponse,
} from '@/types'

export interface UseLeaderboard {
  /** Today's board, ranked by score. */
  daily: DailyLeaderboardResponse | null
  /** All-time board, ranked by Detection Rating. */
  allTime: AllTimeLeaderboardResponse | null
  isLoading: boolean
  error: string | null
  loadDaily: () => Promise<void>
  loadAllTime: () => Promise<void>
}

export function useLeaderboard(): UseLeaderboard {
  const [daily, setDaily] = useState<DailyLeaderboardResponse | null>(null)
  const [allTime, setAllTime] = useState<AllTimeLeaderboardResponse | null>(
    null,
  )
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadDaily = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      setDaily(await leaderboardApi.daily())
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const loadAllTime = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      setAllTime(await leaderboardApi.allTime())
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return { daily, allTime, isLoading, error, loadDaily, loadAllTime }
}
