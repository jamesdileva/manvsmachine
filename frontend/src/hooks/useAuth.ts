/** useAuth: convenience hook over the AuthContext. */

import { useAuthContext, type AuthUser } from '@/contexts/AuthContext'

export interface UseAuth {
  user: AuthUser | null
  isAuthenticated: boolean
  isGuest: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (
    email: string,
    password: string,
    displayName: string,
  ) => Promise<void>
  loginAsGuest: () => Promise<void>
  logout: () => void
}

export function useAuth(): UseAuth {
  const {
    user,
    isAuthenticated,
    isGuest,
    isLoading,
    login,
    register,
    loginAsGuest,
    logout,
  } = useAuthContext()

  return {
    user,
    isAuthenticated,
    isGuest,
    isLoading,
    login: async (email, password) => {
      await login(email, password)
    },
    register: async (email, password, displayName) => {
      await register(email, password, displayName)
    },
    loginAsGuest: async () => {
      await loginAsGuest()
    },
    logout,
  }
}
