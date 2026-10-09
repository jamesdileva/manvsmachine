/** Shared challenge types — mirror the backend schemas (Implementation Guide §10.1). */

export type ConstraintType =
  | 'max_words'
  | 'max_characters'
  | 'must_rhyme'
  | 'no_adjectives'
  | 'must_include_theme'
  | 'exactly_n_emojis'
  | 'no_letter_e'
  | 'one_sentence_only'

/** Constraint as written in the challenge JSON files (camelCase `isHard`). */
export interface Constraint {
  type: ConstraintType
  value: number | string | null
  isHard: boolean
  description?: string
}

export interface ScoringRules {
  baseScore: number
  timeBonusMultiplier: number
  streakMultiplier: number
}

export interface Replayability {
  dailyVariants: number
  constraintPool: string[]
}

/** Full definition as returned by `GET /challenges/{id}` (the file's camelCase shape). */
export interface ChallengeDefinition {
  id: string
  name: string
  interactionType: string
  prompt: string
  constraints: Constraint[]
  timeLimitSeconds: number
  inputType: string
  votingCriteria: string
  difficulty: number
  scoringRules: ScoringRules
  aiPromptTemplateId: string
  aiPromptGuidance: string
  replayability: Replayability
}

/** Constraint as exposed by the API (snake_case endpoints keep the file's `isHard`). */
export interface ConstraintOut {
  type: ConstraintType
  value: number | string | null
  isHard: boolean
}

/** Challenge brief for the daily endpoint (snake_case per §2.2's example). */
export interface ChallengeOut {
  id: string
  name: string
  prompt: string
  constraints: ConstraintOut[]
  time_limit_seconds: number
  input_type: string
  voting_criteria: string
  difficulty: number
}

export interface ConstraintResult {
  valid: boolean
  hard_violations: string[]
  soft_violations: string[]
}

export interface ValidateRequest {
  challenge_id: string
  entry: string
}

export interface ValidateResponse extends ConstraintResult {
  word_count: number
  character_count: number
}
