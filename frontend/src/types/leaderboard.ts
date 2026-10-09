/** Leaderboard types — mirror the backend schemas (Implementation Guide §2.4). */

/** A ranked leaderboard row; daily boards fill `score`, all-time fills `rating`. */
export interface LeaderboardEntry {
  rank: number
  user_id: string
  display_name: string
  score: number | null
  rating: number | null
  accuracy: number | null
}

export interface DailyLeaderboardResponse {
  date: string
  entries: LeaderboardEntry[]
}

export interface AllTimeLeaderboardResponse {
  entries: LeaderboardEntry[]
}
