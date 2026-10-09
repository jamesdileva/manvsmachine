import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '@/routes'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
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
  ])('renders the %s route', (path, heading) => {
    renderAt(path)
    expect(
      screen.getByRole('heading', { name: heading, level: 1 }),
    ).toBeInTheDocument()
  })

  it('renders an unknown route as not found', () => {
    renderAt('/nope')
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument()
  })
})

describe('navigation', () => {
  it('navigates between routes via the nav bar', async () => {
    const user = userEvent.setup()
    renderAt('/')

    await user.click(screen.getByRole('link', { name: 'Leaderboard' }))
    expect(
      screen.getByRole('heading', { name: 'Leaderboard', level: 1 }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: 'Profile' }))
    expect(
      screen.getByRole('heading', { name: 'Profile', level: 1 }),
    ).toBeInTheDocument()
  })

  it('marks the active route in the nav bar', () => {
    renderAt('/leaderboard')
    expect(screen.getByRole('link', { name: 'Leaderboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })
})

describe('home page', () => {
  it('starts a session from the call to action', async () => {
    const user = userEvent.setup()
    renderAt('/')

    await user.click(
      screen.getByRole('button', { name: /play the daily challenge/i }),
    )
    expect(
      screen.getByRole('heading', { name: 'Session', level: 1 }),
    ).toBeInTheDocument()
  })
})

describe('auth page', () => {
  it('renders the sign-in form controls', () => {
    renderAt('/auth')
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Continue as guest' }),
    ).toBeInTheDocument()
  })
})
