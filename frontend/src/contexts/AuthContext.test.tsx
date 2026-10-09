import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { TOKEN_STORAGE_KEY, apiClient } from '@/api/client'
import {
  AuthProvider,
  GUEST_ID_STORAGE_KEY,
  useAuthContext,
} from '@/contexts/AuthContext'
import { AppRoutes } from '@/routes'
import type { AuthResponse } from '@/types'

const TOKEN = 'a.b.c'
const GUEST_ID = 'guest-42'

let mock: MockAdapter

function guestResponse(overrides: Partial<AuthResponse> = {}): AuthResponse {
  return {
    user_id: 'u1',
    guest_id: GUEST_ID,
    display_name: 'Player_1234',
    is_guest: true,
    token: TOKEN,
    ...overrides,
  }
}

beforeEach(() => {
  mock = new MockAdapter(apiClient)
  localStorage.clear()
})

/** Probe component that exposes the auth state. */
function Probe() {
  const { user, isAuthenticated, isGuest, isLoading } = useAuthContext()
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="guest">{String(isGuest)}</span>
      <span data-testid="user">{user?.display_name ?? 'none'}</span>
    </div>
  )
}

function renderApp() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('first visit', () => {
  it('auto-logins as a guest and stores the token + guest id', async () => {
    mock.onPost('/auth/guest').reply(201, guestResponse())

    renderApp()

    await waitFor(() =>
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true'),
    )
    expect(screen.getByTestId('guest')).toHaveTextContent('true')
    expect(screen.getByTestId('user')).toHaveTextContent('Player_1234')
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe(TOKEN)
    expect(localStorage.getItem(GUEST_ID_STORAGE_KEY)).toBe(GUEST_ID)
  })

  it('resumes the persisted guest id instead of creating a new one', async () => {
    localStorage.setItem(GUEST_ID_STORAGE_KEY, GUEST_ID)
    mock
      .onPost('/auth/guest', { guest_id: GUEST_ID })
      .reply(201, guestResponse({ display_name: 'Returner' }))

    renderApp()

    await waitFor(() =>
      expect(screen.getByTestId('user')).toHaveTextContent('Returner'),
    )
  })
})

describe('returning visit', () => {
  it('restores the session by validating the stored token', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, TOKEN)
    mock
      .onGet('/auth/me')
      .reply(200, {
        user_id: 'u1',
        guest_id: null,
        display_name: 'Alex',
        is_guest: false,
      })
      .onPost('/auth/guest')
      .reply(201, guestResponse())

    renderApp()

    await waitFor(() =>
      expect(screen.getByTestId('user')).toHaveTextContent('Alex'),
    )
    expect(screen.getByTestId('guest')).toHaveTextContent('false')
    expect(mock.history.post).toHaveLength(0) // no guest call when the token is valid
  })

  it('falls back to guest login when the stored token is rejected', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'stale.token.here')
    mock
      .onGet('/auth/me')
      .reply(401, { detail: 'invalid or expired token' })
      .onPost('/auth/guest')
      .reply(201, guestResponse())

    renderApp()

    await waitFor(() =>
      expect(screen.getByTestId('guest')).toHaveTextContent('true'),
    )
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe(TOKEN) // replaced by the fresh guest token
  })

  it('stays logged out after a logout across page loads', async () => {
    // Logout clears the token and marks the session as deliberately ended.
    localStorage.setItem('manvsmachine.loggedOut', '1')
    mock
      .onGet('/auth/me')
      .reply(200, { user_id: 'u1', display_name: 'Alex', is_guest: false })

    renderApp()

    await waitFor(() =>
      expect(screen.getByTestId('loading')).toHaveTextContent('false'),
    )
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
    expect(mock.history.post).toHaveLength(0) // no auto-guest
  })
})

describe('auth page', () => {
  function renderAuthPage() {
    return render(
      <MemoryRouter initialEntries={['/auth']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>,
    )
  }

  it('plays as a guest from the auth page and lands home', async () => {
    const user = userEvent.setup()
    mock.onPost('/auth/guest').reply(201, guestResponse())
    renderAuthPage()

    await user.click(
      await screen.findByRole('button', { name: /continue as guest/i }),
    )
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: 'Man vs. Machine', level: 1 }),
      ).toBeInTheDocument(),
    )
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe(TOKEN)
  })

  it('signs in with credentials', async () => {
    const user = userEvent.setup()
    mock
      .onPost('/auth/guest')
      .reply(201, guestResponse())
      .onPost('/auth/login', {
        email: 'alex@example.com',
        password: 'password123',
      })
      .reply(
        200,
        guestResponse({
          is_guest: false,
          display_name: 'Alex',
          guest_id: null,
        }),
      )
    renderAuthPage()

    await user.type(await screen.findByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() =>
      expect(screen.getByTestId('nav-user')).toHaveTextContent('Alex'),
    )
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe(TOKEN)
  })

  it('shows an error when credentials are rejected', async () => {
    const user = userEvent.setup()
    mock
      .onPost('/auth/guest')
      .reply(201, guestResponse())
      .onPost('/auth/login')
      .reply(401, { detail: 'invalid email or password' })
    renderAuthPage()

    await user.type(await screen.findByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'invalid email or password',
    )
  })

  it('registers a new account', async () => {
    const user = userEvent.setup()
    mock
      .onPost('/auth/guest')
      .reply(201, guestResponse())
      .onPost('/auth/register')
      .reply(
        201,
        guestResponse({
          is_guest: false,
          display_name: 'Newbie',
          guest_id: null,
        }),
      )
    renderAuthPage()

    await user.click(
      await screen.findByRole('button', { name: /need an account/i }),
    )
    await user.type(screen.getByLabelText('Display name'), 'Newbie')
    await user.type(screen.getByLabelText('Email'), 'new@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() =>
      expect(screen.getByTestId('nav-user')).toHaveTextContent('Newbie'),
    )
  })
})

describe('route guard', () => {
  it('redirects unauthenticated players to /auth', async () => {
    localStorage.setItem('manvsmachine.loggedOut', '1')
    render(
      <MemoryRouter initialEntries={['/session']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: 'Sign in', level: 1 }),
      ).toBeInTheDocument(),
    )
  })

  it('renders protected routes for authenticated players', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, TOKEN)
    mock
      .onGet('/auth/me')
      .reply(200, { user_id: 'u1', display_name: 'Alex', is_guest: false })
    render(
      <MemoryRouter initialEntries={['/session']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: 'Session', level: 1 }),
      ).toBeInTheDocument(),
    )
  })

  it('logs out from the nav and returns to /auth', async () => {
    const user = userEvent.setup()
    localStorage.setItem(TOKEN_STORAGE_KEY, TOKEN)
    mock
      .onGet('/auth/me')
      .reply(200, { user_id: 'u1', display_name: 'Alex', is_guest: false })
    render(
      <MemoryRouter initialEntries={['/session']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.click(await screen.findByRole('button', { name: /log out/i }))
    expect(
      screen.getByRole('heading', { name: 'Sign in', level: 1 }),
    ).toBeInTheDocument()
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem('manvsmachine.loggedOut')).toBe('1')
  })
})

describe('useAuth guard', () => {
  it('throws when used outside the provider', () => {
    expect(() => render(<Probe />)).toThrow(/AuthProvider/)
  })
})
