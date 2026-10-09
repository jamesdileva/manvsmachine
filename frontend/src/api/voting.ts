/** Voting API: entry submission and votes (Implementation Guide §2.7). */

import { apiClient } from '@/api/client'
import type {
  SubmitEntryRequest,
  SubmitEntryResponse,
  VoteRequest,
  VoteResponse,
} from '@/types'

export const votingApi = {
  /** Stateless practice path: validate an entry and generate the AI entry. */
  submitEntry: async (
    body: SubmitEntryRequest,
  ): Promise<SubmitEntryResponse> => {
    const { data } = await apiClient.post<SubmitEntryResponse>(
      '/voting/submit-entry',
      body,
    )
    return data
  },

  /** Vote on which entry is the AI; returns the reveal and the round's score. */
  vote: async (body: VoteRequest): Promise<VoteResponse> => {
    const { data } = await apiClient.post<VoteResponse>('/voting/vote', body)
    return data
  },
}
