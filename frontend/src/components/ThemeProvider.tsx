/**
 * ThemeProvider: applies the persisted theme to the document (Sprint 23).
 *
 * Tailwind is configured with `darkMode: ['class']`, so light/dark is a
 * `dark` class on <html>; .dark tokens live in styles/globals.css.
 */

import { useEffect, type ReactNode } from 'react'

import { useSettings } from '@/hooks/useSettings'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { theme } = useSettings()
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])
  return <>{children}</>
}
