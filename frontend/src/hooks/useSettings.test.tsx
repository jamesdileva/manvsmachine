import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
} from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import type { ReactNode } from 'react'

import {
  SettingsProvider,
  SETTINGS_STORAGE_KEY,
  useSettings,
} from '@/hooks/useSettings'

function wrapper({ children }: { children: ReactNode }) {
  return <SettingsProvider>{children}</SettingsProvider>
}

function stored() {
  const raw = localStorage.getItem(SETTINGS_STORAGE_KEY)
  return raw ? JSON.parse(raw) : null
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove('dark')
})

describe('useSettings', () => {
  it('defaults to light, stub, sound off', () => {
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.theme).toBe('light')
    expect(result.current.aiProvider).toBe('stub')
    expect(result.current.soundEnabled).toBe(false)
  })

  it('persists each change to localStorage', () => {
    const { result } = renderHook(() => useSettings(), { wrapper })

    act(() => result.current.setTheme('dark'))
    act(() => result.current.setAiProvider('anthropic'))
    act(() => result.current.setSoundEnabled(true))

    expect(stored()).toEqual({
      theme: 'dark',
      aiProvider: 'anthropic',
      soundEnabled: true,
    })
  })

  it('restores saved settings on the next mount', () => {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        theme: 'dark',
        aiProvider: 'openai',
        soundEnabled: true,
      }),
    )

    const { result } = renderHook(() => useSettings(), { wrapper })

    expect(result.current.theme).toBe('dark')
    expect(result.current.aiProvider).toBe('openai')
    expect(result.current.soundEnabled).toBe(true)
  })

  it('falls back to defaults for corrupt stored settings', () => {
    localStorage.setItem(SETTINGS_STORAGE_KEY, 'not json{{')

    const { result } = renderHook(() => useSettings(), { wrapper })

    expect(result.current.theme).toBe('light')
    expect(result.current.aiProvider).toBe('stub')
    expect(result.current.soundEnabled).toBe(false)
  })

  it('shares one state across consumers', () => {
    let seen: string | undefined
    function Probe() {
      const settings = useSettings()
      seen = settings.aiProvider
      return (
        <button onClick={() => settings.setAiProvider('openai')}>pick</button>
      )
    }
    render(
      <SettingsProvider>
        <Probe />
      </SettingsProvider>,
    )
    expect(seen).toBe('stub')
    act(() => {
      fireEvent.click(screen.getByRole('button'))
    })
    expect(seen).toBe('openai')
  })
})
