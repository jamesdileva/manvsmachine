import { describe, expect, it } from 'vitest'

import { checkEntry, countWords } from '@/lib/constraints'
import type { Constraint } from '@/types'

describe('countWords', () => {
  it('counts on whitespace and ignores padding', () => {
    expect(countWords('')).toBe(0)
    expect(countWords('   ')).toBe(0)
    expect(countWords(' fire baked ')).toBe(2)
    expect(countWords('fire baked dragon approved')).toBe(4)
  })
})

describe('checkEntry', () => {
  const of = (...constraints: Constraint[]) => constraints

  it('passes valid entries', () => {
    const result = checkEntry(
      'Fire baked. Dragon approved.',
      of({ type: 'max_words', value: 5, isHard: true }),
    )
    expect(result.valid).toBe(true)
    expect(result.hardViolations).toEqual([])
  })

  it('reports hard violations for over-length entries', () => {
    const result = checkEntry(
      'too many words in this one friend sorry',
      of({ type: 'max_words', value: 5, isHard: true }),
    )
    expect(result.valid).toBe(false)
    expect(result.hardViolations[0]).toContain('too many words')
  })

  it('separates soft violations', () => {
    const result = checkEntry(
      'i keep forgetting to water things oops',
      of({ type: 'must_include_theme', value: 'plant', isHard: false }),
    )
    expect(result.valid).toBe(true)
    expect(result.softViolations[0]).toContain("must mention 'plant'")
  })

  it('checks character limits, the letter e, and sentence count', () => {
    expect(
      checkEntry(
        'abcdefghijk',
        of({ type: 'max_characters', value: 10, isHard: true }),
      ).hardViolations[0],
    ).toContain('too many characters')

    expect(
      checkEntry(
        'the quick brown fox',
        of({ type: 'no_letter_e', value: null, isHard: true }),
      ).hardViolations[0],
    ).toContain("letter 'e'")

    expect(
      checkEntry(
        'one. two.',
        of({ type: 'one_sentence_only', value: null, isHard: true }),
      ).hardViolations[0],
    ).toContain('expected one sentence')
  })

  it('counts emojis without double counting joiners', () => {
    const exact = checkEntry(
      '🎬👨‍💻',
      of({ type: 'exactly_n_emojis', value: 5, isHard: true }),
    )
    expect(exact.hardViolations[0]).toContain('expected exactly 5 emoji(s)')
  })

  it('ignores backend-only constraint types', () => {
    const result = checkEntry(
      'fire and ice',
      of(
        { type: 'must_rhyme', value: null, isHard: true },
        { type: 'no_adjectives', value: null, isHard: true },
      ),
    )
    expect(result.valid).toBe(true)
    expect(result.hardViolations).toEqual([])
  })
})
