import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { EntryInput } from '@/components/EntryInput'
import type { ChallengeDefinition } from '@/types'

const challenge: ChallengeDefinition = {
  id: 'challenge_slogan_01',
  name: 'Tiny Tagline',
  interactionType: 'Quick Text',
  prompt: 'Write a slogan for a dragon-owned bakery.',
  constraints: [{ type: 'max_words', value: 5, isHard: true }],
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
  aiPromptGuidance: '',
  replayability: { dailyVariants: 3, constraintPool: [] },
}

function setup(overrides: Partial<Parameters<typeof EntryInput>[0]> = {}) {
  const onSubmit = vi.fn()
  const onChange = vi.fn()
  const utils = render(
    <EntryInput
      challenge={challenge}
      value=""
      onChange={onChange}
      onSubmit={onSubmit}
      {...overrides}
    />,
  )
  return { onSubmit, onChange, user: userEvent.setup(), ...utils }
}

describe('EntryInput', () => {
  it('updates the live word count as the user types', async () => {
    const { onChange, user } = setup()
    await user.type(screen.getByRole('textbox'), 'fire baked')
    expect(onChange).toHaveBeenCalled()
    // Controlled: rerender with the typed value to show the counts.
    render(
      <EntryInput
        challenge={challenge}
        value="fire baked"
        onChange={onChange}
        onSubmit={vi.fn()}
      />,
    )
    expect(screen.getAllByTestId('entry-counts')[1]).toHaveTextContent(
      '2 words / 5',
    )
  })

  it('disables submit while a hard violation stands', () => {
    setup({ value: 'too many words in this friend' })
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled()
    expect(screen.getByTestId('hard-violations')).toHaveTextContent(
      'too many words',
    )
  })

  it('enables submit for a valid entry and calls onSubmit', async () => {
    const { onSubmit, user } = setup({ value: 'Fire baked. Dragon approved.' })
    const button = screen.getByRole('button', { name: 'Submit' })
    expect(button).toBeEnabled()
    expect(screen.queryByTestId('hard-violations')).not.toBeInTheDocument()
    await user.click(button)
    expect(onSubmit).toHaveBeenCalledWith('Fire baked. Dragon approved.')
  })

  it('shows soft violations without blocking', () => {
    setup({
      value: 'short one',
      challenge: {
        ...challenge,
        constraints: [
          { type: 'max_words', value: 5, isHard: true },
          { type: 'must_include_theme', value: 'bread', isHard: false },
        ],
      },
    })
    expect(screen.getByTestId('soft-violations')).toHaveTextContent(
      "must mention 'bread'",
    )
    expect(screen.getByRole('button', { name: 'Submit' })).toBeEnabled()
  })

  it('renders a textarea for multi-line inputs', () => {
    setup({
      challenge: { ...challenge, inputType: 'text_multi_line' },
    })
    expect(screen.getByRole('textbox').tagName).toBe('TEXTAREA')
  })

  it('respects the disabled flag', () => {
    setup({ value: 'Fire baked.', disabled: true })
    expect(screen.getByRole('textbox')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled()
  })
})
