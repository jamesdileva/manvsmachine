import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

interface ChartInstance {
  canvas: unknown
  config: unknown
  destroyed: boolean
}

const chartInstances: ChartInstance[] = []

vi.mock('chart.js', () => {
  class Chart {
    constructor(
      public canvas: unknown,
      public config: unknown,
    ) {
      chartInstances.push({ canvas, config, destroyed: false })
    }
    destroy() {
      chartInstances.forEach((entry) => (entry.destroyed = true))
    }
  }
  return { Chart }
})

import { apiClient } from '@/api/client'
import Profile from '@/pages/profile'
import type { AuthResponse, ProfileResponse } from '@/types'
import { renderWithProviders } from '@/test/utils'

let mock: MockAdapter

const profile: ProfileResponse = {
  user_id: 'u1',
  display_name: 'Player_1234',
  is_guest: true,
  detection_rating: 1012,
  total_rounds: 47,
  overall_accuracy: 62.3,
  current_streak: 3,
  longest_streak: 7,
  daily_challenge_streak: 5,
  recent_humanity_scores: [
    { challenge_id: 'challenge_slogan_01', score: 68, date: '2026-10-08' },
    { challenge_id: 'challenge_emoji_03', score: 84, date: '2026-10-09' },
  ],
}

beforeEach(() => {
  mock = new MockAdapter(apiClient)
  chartInstances.length = 0
  localStorage.clear()
  mock.onPost('/auth/guest').reply(201, {
    user_id: 'u1',
    guest_id: 'g1',
    display_name: 'Player_1234',
    is_guest: true,
    token: 'a.b.c',
  } satisfies AuthResponse)
})

describe('Profile page', () => {
  it('shows every stat and streak from the profile', async () => {
    mock.onGet('/profile').reply(200, profile)

    renderWithProviders(<Profile />)

    expect(await screen.findByDisplayValue('Player_1234')).toBeInTheDocument()
    expect(screen.getByTestId('profile-rating')).toHaveTextContent('1012')
    expect(screen.getByTestId('profile-rounds')).toHaveTextContent('47')
    expect(screen.getByTestId('profile-accuracy')).toHaveTextContent('62.3%')
    expect(screen.getByTestId('profile-current-streak')).toHaveTextContent('3')
    expect(screen.getByTestId('profile-longest-streak')).toHaveTextContent('7')
    expect(screen.getByTestId('profile-daily-streak')).toHaveTextContent('5')
    expect(screen.getByTestId('streak-badge')).toHaveTextContent('3-day streak')
  })

  it('renders a humanity meter per recent entry', async () => {
    mock.onGet('/profile').reply(200, profile)

    renderWithProviders(<Profile />)

    expect(
      await screen.findByRole('progressbar', {
        name: 'challenge_slogan_01 humanity score',
      }),
    ).toHaveAttribute('aria-valuenow', '68')
    expect(
      screen.getByRole('progressbar', {
        name: 'challenge_emoji_03 humanity score',
      }),
    ).toHaveAttribute('aria-valuenow', '84')
  })

  it('renders the humanity trend chart with the recent scores', async () => {
    mock.onGet('/profile').reply(200, profile)

    renderWithProviders(<Profile />)

    expect(await screen.findByTestId('humanity-trend')).toBeInTheDocument()
    expect(chartInstances).toHaveLength(1)
    const config = chartInstances[0].config as {
      type: string
      data: { labels: string[]; datasets: { data: number[] }[] }
    }
    expect(config.type).toBe('line')
    expect(config.data.labels).toEqual(['2026-10-08', '2026-10-09'])
    expect(config.data.datasets[0].data).toEqual([68, 84])
  })

  it('saves a new display name via PUT /profile', async () => {
    mock.onGet('/profile').reply(200, profile)
    mock
      .onPut('/profile', { display_name: 'DragonBakery' })
      .reply(200, { ...profile, display_name: 'DragonBakery' })

    renderWithProviders(<Profile />)
    await screen.findByDisplayValue('Player_1234')

    const input = screen.getByDisplayValue('Player_1234')
    await userEvent.clear(input)
    await userEvent.type(input, 'DragonBakery')
    await userEvent.click(screen.getByRole('button', { name: /save/i }))

    expect(await screen.findByDisplayValue('DragonBakery')).toBeInTheDocument()
  })

  it('shows an error when the profile fails to load', async () => {
    mock.onGet('/profile').reply(500, { detail: 'no profile' })

    renderWithProviders(<Profile />)

    expect(await screen.findByText(/no profile/i)).toBeInTheDocument()
  })
})
