import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import type { ReactNode } from 'react'

import { ThemeProvider } from '@/components/ThemeProvider'
import { SettingsProvider } from '@/hooks/useSettings'
import { SETTINGS_STORAGE_KEY } from '@/hooks/useSettings'

function tree({ children }: { children: ReactNode }) {
  return (
    <SettingsProvider>
      <ThemeProvider>{children}</ThemeProvider>
    </SettingsProvider>
  )
}

function seed(settings: Record<string, unknown>) {
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove('dark')
})

describe('ThemeProvider', () => {
  it('renders children', () => {
    render(<span>child</span>, { wrapper: tree })
    expect(screen.getByText('child')).toBeInTheDocument()
  })

  it('applies the dark class for a dark theme', () => {
    seed({ theme: 'dark', aiProvider: 'stub', soundEnabled: false })
    render(<span>x</span>, { wrapper: tree })
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('does not apply the dark class for a light theme', () => {
    seed({ theme: 'light', aiProvider: 'stub', soundEnabled: false })
    render(<span>x</span>, { wrapper: tree })
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('defaults to the light theme with no stored settings', () => {
    render(<span>x</span>, { wrapper: tree })
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
