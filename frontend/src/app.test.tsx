import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { apiClient } from '@/api/client'
import App from '@/app'
import type { AuthResponse } from '@/types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
  localStorage.clear()
  // Every app load auto-grabs a guest session; the nav reads the auth state.
  mock.onPost('/auth/guest').reply(201, {
    user_id: 'u1',
    guest_id: 'g1',
    display_name: 'Player_1234',
    is_guest: true,
    token: 'a.b.c',
  } satisfies AuthResponse)
  // The Challenge page loads today's challenge (daily brief + full definition).
  mock
    .onGet('/challenges/daily')
    .reply(200, {
      challenge: {
        id: 'challenge_slogan_01',
        name: 'Tiny Tagline',
        prompt: 'Write a slogan for a dragon-owned bakery.',
        constraints: [{ type: 'max_words', value: 5, isHard: true }],
        time_limit_seconds: 15,
        input_type: 'text_single_line',
        voting_criteria: 'most_believable',
        difficulty: 2,
      },
      session_id: 's1',
      round_number: 1,
      round_id: 'r1',
    })
    .onGet('/challenges/challenge_slogan_01')
    .reply(200, {
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
      aiPromptGuidance: 'Be casual.',
      replayability: { dailyVariants: 3, constraintPool: [] },
    })
})

function renderAt(path: string) {
  window.history.pushState({}, '', path)
  return render(<App />)
}

describe('routing', () => {
  it.each([
    ['/', 'Man vs. Machine'],
    ['/session', 'Session'],
    ['/challenge', 'Challenge'],
    ['/leaderboard', 'Leaderboard'],
    ['/profile', 'Profile'],
    ['/auth', 'Sign in'],
    ['/settings', 'Settings'],
  ])('renders the %s route', async (path, heading) => {
    renderAt(path)
    expect(
      await screen.findByRole('heading', { name: heading, level: 1 }),
    ).toBeInTheDocument()
  })

  it('renders an unknown route as not found', async () => {
    renderAt('/nope')
    expect(await screen.findByText('Page not found')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument()
  })
})

describe('navigation', () => {
  it('navigates between routes via the nav bar', async () => {
    const user = userEvent.setup()
    renderAt('/')
    await screen.findByRole('heading', { name: 'Man vs. Machine', level: 1 })

    await user.click(screen.getByRole('link', { name: 'Leaderboard' }))
    expect(
      screen.getByRole('heading', { name: 'Leaderboard', level: 1 }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: 'Profile' }))
    expect(
      screen.getByRole('heading', { name: 'Profile', level: 1 }),
    ).toBeInTheDocument()
  })

  it('marks the active route in the nav bar', async () => {
    renderAt('/leaderboard')
    expect(
      await screen.findByRole('link', { name: 'Leaderboard' }),
    ).toHaveAttribute('aria-current', 'page')
  })
})

describe('home page', () => {
  it('starts a session from the call to action', async () => {
    const user = userEvent.setup()
    renderAt('/')

    await user.click(
      await screen.findByRole('button', { name: /play the daily challenge/i }),
    )
    expect(
      screen.getByRole('heading', { name: 'Session', level: 1 }),
    ).toBeInTheDocument()
  })
})

describe('auth page', () => {
  it('renders the sign-in form controls', async () => {
    renderAt('/auth')
    expect(await screen.findByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Continue as guest' }),
    ).toBeInTheDocument()
  })
})
