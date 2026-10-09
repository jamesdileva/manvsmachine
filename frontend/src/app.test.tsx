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
