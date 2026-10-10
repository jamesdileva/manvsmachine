/**
 * useScoring: the scoring slice of the live session channel.
 */

import {
  useScoringContext,
  type ScoringContextValue,
} from '@/contexts/ScoringContext'

export type UseScoring = ScoringContextValue

export function useScoring(): UseScoring {
  return useScoringContext()
}
