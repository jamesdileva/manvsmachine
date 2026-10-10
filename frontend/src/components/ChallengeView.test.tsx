import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ChallengeView } from '@/components/ChallengeView'
import type { ChallengeDefinition } from '@/types'

const challenge: ChallengeDefinition = {
  id: 'challenge_slogan_01',
  name: 'Tiny Tagline',
  interactionType: 'Quick Text',
  prompt: 'Write a slogan for a dragon-owned bakery.',
  constraints: [
    { type: 'max_words', value: 5, isHard: true },
    {
      type: 'must_include_theme',
      value: 'bread',
      isHard: false,
      description: 'Mention bread',
    },
  ],
  timeLimitSeconds: 15,
  inputType: 'text_single_line',
  votingCriteria: 'most_believable',
  difficulty: 2,
  scoringRules: {
    baseScore: 100,
    timeBonusMultiplier: 0.15,
    streakMultiplier: 0.05,
  },
  aiPromptTemplateId: 'v1.0',
  aiPromptGuidance: 'Be casual.',
  replayability: { dailyVariants: 3, constraintPool: [] },
}

describe('ChallengeView', () => {
  it('renders the prompt, constraints, difficulty, and time limit', () => {
    render(<ChallengeView challenge={challenge} />)

    expect(
      screen.getByText('Write a slogan for a dragon-owned bakery.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Medium')).toBeInTheDocument()
    expect(screen.getByText('15s')).toBeInTheDocument()
    expect(screen.getByText('Mention bread')).toBeInTheDocument()
    expect(
      screen.getByText('Vote on which entry is the AI — most believable.'),
    ).toBeInTheDocument()
  })

  it('labels hard vs soft constraints', () => {
    render(<ChallengeView challenge={challenge} />)
    expect(screen.getByText('required')).toBeInTheDocument()
    expect(screen.getByText('bonus')).toBeInTheDocument()
  })

  it('renders extra content (timer, input) under the prompt', () => {
    render(
      <ChallengeView challenge={challenge}>
        <div data-testid="child-content">timer here</div>
      </ChallengeView>,
    )
    expect(screen.getByTestId('child-content')).toBeInTheDocument()
  })
})
