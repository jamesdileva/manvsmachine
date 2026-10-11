import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { apiClient } from '@/api/client'
import Leaderboard from '@/pages/leaderboard'
import type { AuthResponse } from '@/types'
import { renderWithProviders } from '@/test/utils'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
  localStorage.clear()
  // Protected route: the auth context grabs a guest session on mount.
  mock.onPost('/auth/guest').reply(201, {
    user_id: 'u1',
    guest_id: 'g1',
    display_name: 'Player_1234',
    is_guest: true,
    token: 'a.b.c',
  } satisfies AuthResponse)
  mock.onGet('/leaderboard/daily').reply(200, {
    date: '2026-10-10',
    entries: [
      {
        rank: 1,
        user_id: 'u1',
        display_name: 'Alex',
        score: 300,
        rating: null,
        accuracy: 100,
      },
    ],
  })
  mock.onGet('/leaderboard/all-time').reply(200, {
    entries: [
      {
        rank: 1,
        user_id: 'u1',
        display_name: 'Alex',
        score: null,
        rating: 1450,
        accuracy: 100,
      },
    ],
  })
})

describe('Leaderboard page', () => {
  it('shows the daily board by default', async () => {
    renderWithProviders(<Leaderboard />)

    expect(await screen.findByText('Alex')).toBeInTheDocument()
    expect(screen.getByText('300')).toBeInTheDocument()
    expect(screen.queryByText('1450')).not.toBeInTheDocument()
  })

  it('switches to the all-time board ranked by rating', async () => {
    renderWithProviders(<Leaderboard />)
    await screen.findByText('Alex')

    await userEvent.click(screen.getByRole('tab', { name: /all-time/i }))

    expect(await screen.findByText('1450')).toBeInTheDocument()
    expect(screen.queryByText('300')).not.toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /all-time/i })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  it('shows an error when the daily board fails to load', async () => {
    mock.onGet('/leaderboard/daily').reply(500, { detail: 'board unavailable' })

    renderWithProviders(<Leaderboard />)

    expect(await screen.findByText(/board unavailable/i)).toBeInTheDocument()
  })
})
