/**
 * useSettings: player preferences persisted in localStorage (Sprint 23).
 *
 * One store behind `SettingsProvider`/`useSettings` so the Settings page and
 * ThemeProvider always see the same state. Reads on mount, writes on change;
 * corrupt or unknown values fall back to defaults.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

/** localStorage key for the persisted preferences object. */
export const SETTINGS_STORAGE_KEY = 'manvsmachine.settings'

export const THEMES = ['light', 'dark'] as const
export type ThemeName = (typeof THEMES)[number]

/** The provider the local backend prefers for AI entries (backend env decides). */
export const AI_PROVIDERS = ['openai', 'anthropic', 'stub'] as const
export type AiProviderName = (typeof AI_PROVIDERS)[number]

export interface Settings {
  theme: ThemeName
  aiProvider: AiProviderName
  soundEnabled: boolean
}

const DEFAULTS: Settings = {
  theme: 'light',
  aiProvider: 'stub',
  soundEnabled: false,
}

interface SettingsContextValue extends Settings {
  setTheme: (theme: ThemeName) => void
  setAiProvider: (provider: AiProviderName) => void
  setSoundEnabled: (enabled: boolean) => void
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

function readStored(): Settings {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (!raw) return DEFAULTS
    const parsed = JSON.parse(raw) as Partial<Settings>
    return {
      theme: parsed.theme === 'dark' ? 'dark' : DEFAULTS.theme,
      aiProvider: AI_PROVIDERS.includes(parsed.aiProvider as AiProviderName)
        ? (parsed.aiProvider as AiProviderName)
        : DEFAULTS.aiProvider,
      soundEnabled:
        typeof parsed.soundEnabled === 'boolean'
          ? parsed.soundEnabled
          : DEFAULTS.soundEnabled,
    }
  } catch {
    return DEFAULTS
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(readStored)

  const update = useCallback((patch: Partial<Settings>) => {
    setSettings((current) => {
      const next = { ...current, ...patch }
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const value = useMemo<SettingsContextValue>(
    () => ({
      ...settings,
      setTheme: (theme) => update({ theme }),
      setAiProvider: (aiProvider) => update({ aiProvider }),
      setSoundEnabled: (soundEnabled) => update({ soundEnabled }),
    }),
    [settings, update],
  )

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings(): SettingsContextValue {
  const value = useContext(SettingsContext)
  if (value === null) {
    throw new Error('useSettings must be used inside a SettingsProvider')
  }
  return value
}
