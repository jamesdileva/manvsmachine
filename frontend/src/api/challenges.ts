/** Challenges API: daily challenge, definitions, entry validation. */

import { apiClient } from '@/api/client'
import type {
  ChallengeDefinition,
  DailyChallengeResponse,
  ValidateRequest,
  ValidateResponse,
} from '@/types'

export const challengesApi = {
  /** Today's challenge; creates/reuses the player's daily session. */
  daily: async (playerRating?: number): Promise<DailyChallengeResponse> => {
    const { data } = await apiClient.get<DailyChallengeResponse>(
      '/challenges/daily',
      {
        params:
          playerRating === undefined
            ? undefined
            : { player_rating: playerRating },
      },
    )
    return data
  },

  byId: async (challengeId: string): Promise<ChallengeDefinition> => {
    const { data } = await apiClient.get<ChallengeDefinition>(
      `/challenges/${challengeId}`,
    )
    return data
  },

  /** Soft-check an entry against a challenge's constraints (pre-submission hint). */
  validate: async (body: ValidateRequest): Promise<ValidateResponse> => {
    const { data } = await apiClient.post<ValidateResponse>(
      '/challenges/validate',
      body,
    )
    return data
  },
}
