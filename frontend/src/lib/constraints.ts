/**
 * Client-side constraint checks for live input feedback.
 *
 * Mirrors the backend ConstraintEngine's semantics (hard blocks, soft warns) for
 * the types a browser can evaluate deterministically. The server remains the
 * authority: `/challenges/validate` and the submission endpoint re-check
 * everything, and heuristic constraints (must_rhyme, no_adjectives) are
 * backend-only.
 */

import type { Constraint, ConstraintType } from '@/types'

export interface ConstraintCheck {
  valid: boolean
  hardViolations: string[]
  softViolations: string[]
}

const EMOJI_RE =
  /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F1E6}-\u{1F1FF}\u{2B00}-\u{2BFF}\u{1F900}-\u{1F9FF}]/gu

/** Constraint types the client can evaluate; the rest are backend-only. */
export const CLIENT_CHECKABLE: ReadonlySet<ConstraintType> =
  new Set<ConstraintType>([
    'max_words',
    'max_characters',
    'must_include_theme',
    'exactly_n_emojis',
    'no_letter_e',
    'one_sentence_only',
  ])

export function isClientCheckable(constraint: Constraint): boolean {
  return CLIENT_CHECKABLE.has(constraint.type)
}

/** Evaluate an entry against a challenge's constraints. */
export function checkEntry(
  entry: string,
  constraints: Constraint[],
): ConstraintCheck {
  const hardViolations: string[] = []
  const softViolations: string[] = []
  for (const constraint of constraints) {
    if (!isClientCheckable(constraint)) continue
    const violation = checkConstraint(entry, constraint)
    if (violation) {
      ;(constraint.isHard ? hardViolations : softViolations).push(violation)
    }
  }
  return { valid: hardViolations.length === 0, hardViolations, softViolations }
}

export function checkConstraint(
  entry: string,
  constraint: Constraint,
): string | null {
  switch (constraint.type) {
    case 'max_words': {
      const count = entry.trim() ? entry.trim().split(/\s+/).length : 0
      const limit = Number(constraint.value)
      return count > limit ? `too many words (${count} > ${limit})` : null
    }
    case 'max_characters': {
      const limit = Number(constraint.value)
      return entry.length > limit
        ? `too many characters (${entry.length} > ${limit})`
        : null
    }
    case 'must_include_theme': {
      const theme = String(constraint.value ?? '').toLowerCase()
      return theme && !entry.toLowerCase().includes(theme)
        ? `must mention '${constraint.value}'`
        : null
    }
    case 'exactly_n_emojis': {
      const found = entry.match(EMOJI_RE)?.length ?? 0
      const expected = Number(constraint.value)
      return found !== expected
        ? `expected exactly ${expected} emoji(s), found ${found}`
        : null
    }
    case 'no_letter_e':
      return entry.toLowerCase().includes('e')
        ? "contains the letter 'e'"
        : null
    case 'one_sentence_only': {
      const sentences = entry.split(/[.!?]+/).filter((part) => part.trim())
      return sentences.length > 1
        ? `expected one sentence, found ${sentences.length}`
        : null
    }
    default:
      return null
  }
}

/** Live word/character counts for the input footer. */
export function countWords(entry: string): number {
  return entry.trim() ? entry.trim().split(/\s+/).length : 0
}
