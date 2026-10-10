/** useChallenges: daily challenge lookup, definitions, and entry validation. */

import { useCallback, useState } from 'react'

import { challengesApi } from '@/api/challenges'
import { toApiError } from '@/api/errors'
import type {
  ChallengeDefinition,
  DailyChallengeResponse,
  ValidateResponse,
} from '@/types'

export interface UseChallenges {
  /** Today's challenge plus the player's daily session. */
  daily: DailyChallengeResponse | null
  /** The full definition currently being shown. */
  challenge: ChallengeDefinition | null
  isLoading: boolean
  error: string | null
  loadDaily: () => Promise<void>
  loadChallenge: (challengeId: string) => Promise<ChallengeDefinition | null>
  /** Server-side pre-submission validation. */
  validateEntry: (
    challengeId: string,
    entry: string,
  ) => Promise<ValidateResponse | null>
}

export function useChallenges(): UseChallenges {
  const [daily, setDaily] = useState<DailyChallengeResponse | null>(null)
  const [challenge, setChallenge] = useState<ChallengeDefinition | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadDaily = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await challengesApi.daily()
      setDaily(response)
      setChallenge(await challengesApi.byId(response.challenge.id))
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const loadChallenge = useCallback(
    async (challengeId: string): Promise<ChallengeDefinition | null> => {
      setIsLoading(true)
      setError(null)
      try {
        const definition = await challengesApi.byId(challengeId)
        setChallenge(definition)
        return definition
      } catch (caught) {
        setError(toApiError(caught).message)
        return null
      } finally {
        setIsLoading(false)
      }
    },
    [],
  )

  const validateEntry = useCallback(
    async (
      challengeId: string,
      entry: string,
    ): Promise<ValidateResponse | null> => {
      try {
        return await challengesApi.validate({
          challenge_id: challengeId,
          entry,
        })
      } catch (caught) {
        setError(toApiError(caught).message)
        return null
      }
    },
    [],
  )

  return {
    daily,
    challenge,
    isLoading,
    error,
    loadDaily,
    loadChallenge,
    validateEntry,
  }
}
