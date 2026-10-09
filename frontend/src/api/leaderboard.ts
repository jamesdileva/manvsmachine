/** Leaderboard API: daily and all-time boards (Implementation Guide §2.4). */

import { apiClient } from '@/api/client'
import type {
  AllTimeLeaderboardResponse,
  DailyLeaderboardResponse,
} from '@/types'

export const leaderboardApi = {
  /** Today's board, or `?date=YYYY-MM-DD` for a past day. */
  daily: async (params?: {
    date?: string
    limit?: number
  }): Promise<DailyLeaderboardResponse> => {
    const { data } = await apiClient.get<DailyLeaderboardResponse>(
      '/leaderboard/daily',
      {
        params,
      },
    )
    return data
  },

  allTime: async (limit?: number): Promise<AllTimeLeaderboardResponse> => {
    const { data } = await apiClient.get<AllTimeLeaderboardResponse>(
      '/leaderboard/all-time',
      {
        params: limit === undefined ? undefined : { limit },
      },
    )
    return data
  },
}
