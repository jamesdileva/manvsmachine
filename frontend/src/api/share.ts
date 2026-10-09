/** Share API: shareable result summaries (Implementation Guide §2.6; backend in Sprint 25). */

import { apiClient } from '@/api/client'
import type { ShareRequest, ShareResponse } from '@/types'

export const shareApi = {
  result: async (body: ShareRequest): Promise<ShareResponse> => {
    const { data } = await apiClient.post<ShareResponse>('/share/result', body)
    return data
  },
}
