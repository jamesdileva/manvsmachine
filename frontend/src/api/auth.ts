/** Auth API: guest sessions, register, login, current user. */

import { apiClient } from '@/api/client'
import type {
  AuthResponse,
  GuestAuthRequest,
  LoginRequest,
  MeResponse,
  RegisterRequest,
} from '@/types'

export const authApi = {
  /** Play as a guest (optionally resuming a known guest_id). */
  guest: async (body: GuestAuthRequest = {}): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>('/auth/guest', body)
    return data
  },

  register: async (body: RegisterRequest): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>('/auth/register', body)
    return data
  },

  login: async (body: LoginRequest): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>('/auth/login', body)
    return data
  },

  me: async (): Promise<MeResponse> => {
    const { data } = await apiClient.get<MeResponse>('/auth/me')
    return data
  },
}
