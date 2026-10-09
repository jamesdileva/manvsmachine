/**
 * AuthContext: JWT session state for the app.
 *
 * On first load the stored token is validated via `/auth/me`; with no token the
 * player is auto-logged-in as a guest (resuming the persisted guest_id when
 * present). Logout clears the token and marks the session as deliberately ended,
 * so a page reload does not silently re-guest.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { authApi } from '@/api/auth'
import { TOKEN_STORAGE_KEY } from '@/api/client'
import type {
  AuthResponse,
  LoginRequest,
  MeResponse,
  RegisterRequest,
} from '@/types'

/** Persisted guest identity so a returning visitor resumes the same account. */
export const GUEST_ID_STORAGE_KEY = 'manvsmachine.guestId'
/** Set by logout so auto-guest does not undo it on the next page load. */
const LOGGED_OUT_STORAGE_KEY = 'manvsmachine.loggedOut'

/** The signed-in player (shared by auth and /auth/me responses). */
export interface AuthUser {
  user_id: string
  guest_id: string | null
  display_name: string
  is_guest: boolean
}

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isGuest: boolean
  /** True until the stored session has been resolved on load. */
  isLoading: boolean
  login: (email: string, password: string) => Promise<AuthResponse>
  register: (
    email: string,
    password: string,
    displayName: string,
  ) => Promise<AuthResponse>
  loginAsGuest: () => Promise<AuthResponse>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function toUser(response: AuthResponse | MeResponse): AuthUser {
  return {
    user_id: response.user_id,
    guest_id: response.guest_id,
    display_name: response.display_name,
    is_guest: response.is_guest,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  /** Store a fresh token + identity, and clear any logged-out marker. */
  const persist = useCallback((response: AuthResponse): AuthResponse => {
    localStorage.setItem(TOKEN_STORAGE_KEY, response.token)
    if (response.guest_id) {
      localStorage.setItem(GUEST_ID_STORAGE_KEY, response.guest_id)
    }
    localStorage.removeItem(LOGGED_OUT_STORAGE_KEY)
    setUser(toUser(response))
    return response
  }, [])

  const loginAsGuest = useCallback(async (): Promise<AuthResponse> => {
    const storedGuestId = localStorage.getItem(GUEST_ID_STORAGE_KEY)
    const response = await authApi.guest(
      storedGuestId ? { guest_id: storedGuestId } : {},
    )
    return persist(response)
  }, [persist])

  const login = useCallback(
    async (email: string, password: string) => {
      const body: LoginRequest = { email, password }
      return persist(await authApi.login(body))
    },
    [persist],
  )

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      const body: RegisterRequest = {
        email,
        password,
        display_name: displayName,
      }
      return persist(await authApi.register(body))
    },
    [persist],
  )

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.setItem(LOGGED_OUT_STORAGE_KEY, '1')
    setUser(null)
  }, [])

  // Resolve the stored session once on mount.
  useEffect(() => {
    let cancelled = false

    async function restore() {
      const token = localStorage.getItem(TOKEN_STORAGE_KEY)
      try {
        if (token) {
          const me = await authApi.me()
          if (!cancelled) setUser(toUser(me))
          return
        }
        if (!localStorage.getItem(LOGGED_OUT_STORAGE_KEY)) {
          await loginAsGuest()
        }
      } catch {
        // A stale/invalid token is dropped; first visitors still get a guest.
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        if (!localStorage.getItem(LOGGED_OUT_STORAGE_KEY)) {
          try {
            await loginAsGuest()
          } catch {
            /* offline or backend down: stay unauthenticated */
          }
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void restore()
    return () => {
      cancelled = true
    }
  }, [loginAsGuest])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isGuest: user?.is_guest ?? false,
      isLoading,
      login,
      register,
      loginAsGuest,
      logout,
    }),
    [user, isLoading, login, register, loginAsGuest, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuthContext must be used inside an AuthProvider')
  }
  return context
}
