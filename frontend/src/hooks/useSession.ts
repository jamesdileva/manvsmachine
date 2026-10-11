/** useSession: the game-loop state and actions. */

import {
  useSessionContext,
  type SessionContextValue,
} from '@/contexts/SessionContext'

export type UseSession = SessionContextValue

export function useSession(): UseSession {
  return useSessionContext()
}
