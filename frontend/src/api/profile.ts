/** Profile API: current player's stats and display name (Implementation Guide §2.5). */

import { apiClient } from '@/api/client'
import type { ProfileResponse, ProfileUpdateRequest } from '@/types'

export const profileApi = {
  get: async (): Promise<ProfileResponse> => {
    const { data } = await apiClient.get<ProfileResponse>('/profile')
    return data
  },

  update: async (body: ProfileUpdateRequest): Promise<ProfileResponse> => {
    const { data } = await apiClient.put<ProfileResponse>('/profile', body)
    return data
  },
}
