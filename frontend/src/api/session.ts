/** Session API: start, state, summary, round advance, and round entry submission. */

import { apiClient } from '@/api/client'
import type {
  NextRoundResponse,
  RoundSubmission,
  SessionStartRequest,
  SessionStartResponse,
  SessionStateResponse,
  SessionSummaryResponse,
} from '@/types'

export const sessionApi = {
  start: async (body: SessionStartRequest): Promise<SessionStartResponse> => {
    const { data } = await apiClient.post<SessionStartResponse>(
      '/session/start',
      body,
    )
    return data
  },

  state: async (sessionId: string): Promise<SessionStateResponse> => {
    const { data } = await apiClient.get<SessionStateResponse>(
      `/session/${sessionId}`,
    )
    return data
  },

  summary: async (sessionId: string): Promise<SessionSummaryResponse> => {
    const { data } = await apiClient.get<SessionSummaryResponse>(
      `/session/${sessionId}/summary`,
    )
    return data
  },

  /** Advance to the next round; `complete` is true once every round is played. */
  next: async (sessionId: string): Promise<NextRoundResponse> => {
    const { data } = await apiClient.post<NextRoundResponse>(
      `/session/${sessionId}/next`,
    )
    return data
  },

  /** Submit the human entry for a round; returns both entries anonymized as A/B. */
  submitEntry: async (
    sessionId: string,
    roundId: string,
    entry: string,
  ): Promise<RoundSubmission> => {
    const { data } = await apiClient.post<RoundSubmission>(
      `/session/${sessionId}/rounds/${roundId}/entry`,
      { entry },
    )
    return data
  },
}
