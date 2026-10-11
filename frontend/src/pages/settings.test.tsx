import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import type { ReactNode } from 'react'

import { ThemeProvider } from '@/components/ThemeProvider'
import { SettingsProvider, SETTINGS_STORAGE_KEY } from '@/hooks/useSettings'
import Settings from '@/pages/settings'

function tree({ children }: { children: ReactNode }) {
  return (
    <SettingsProvider>
      <ThemeProvider>{children}</ThemeProvider>
    </SettingsProvider>
  )
}

function stored() {
  const raw = localStorage.getItem(SETTINGS_STORAGE_KEY)
  return raw ? JSON.parse(raw) : null
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove('dark')
})

describe('Settings page', () => {
  it('renders the AI provider, theme, and sound controls', () => {
    render(<Settings />, { wrapper: tree })

    expect(
      screen.getByRole('heading', { name: 'Settings', level: 1 }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/ai provider/i)).toBeInTheDocument()
    expect(
      screen.getByRole('switch', { name: /dark mode/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: /sound/i })).toBeInTheDocument()
  })

  it('persists the AI provider selection', async () => {
    render(<Settings />, { wrapper: tree })
    await userEvent.selectOptions(
      screen.getByLabelText(/ai provider/i),
      'anthropic',
    )
    expect(stored().aiProvider).toBe('anthropic')
    expect(
      screen.getByRole('option', { name: /anthropic/i }),
    ).toBeInTheDocument()
  })

  it('persists the theme toggle and flips the html class', async () => {
    render(<Settings />, { wrapper: tree })
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    await userEvent.click(screen.getByRole('switch', { name: /dark mode/i }))

    expect(stored().theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('persists the sound toggle', async () => {
    render(<Settings />, { wrapper: tree })

    await userEvent.click(screen.getByRole('switch', { name: /sound/i }))

    expect(stored().soundEnabled).toBe(true)
    expect(screen.getByRole('switch', { name: /sound/i })).toBeChecked()
  })

  it('restores saved values into the controls', () => {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        theme: 'dark',
        aiProvider: 'openai',
        soundEnabled: true,
      }),
    )
    render(<Settings />, { wrapper: tree })

    expect(screen.getByLabelText(/ai provider/i)).toHaveValue('openai')
    expect(screen.getByRole('switch', { name: /dark mode/i })).toBeChecked()
    expect(screen.getByRole('switch', { name: /sound/i })).toBeChecked()
  })
})
