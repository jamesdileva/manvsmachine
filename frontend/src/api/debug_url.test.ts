import { describe, expect, it } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { apiClient } from '@/api/client'
import { challengesApi } from '@/api/challenges'

describe('debug', () => {
  it('shows the requested url', async () => {
    const mock = new MockAdapter(apiClient)
    mock.onAny().reply((config) => {
      console.log(
        'REQUEST URL:',
        config.url,
        'BASE:',
        config.baseURL,
        'PARAMS:',
        JSON.stringify(config.params),
      )
      return [200, {}]
    })
    await challengesApi.daily().catch(() => {})
    console.log(
      'HISTORY:',
      mock.history.get.map((r) => r.url),
    )
    expect(true).toBe(true)
  })
})
