/** Settings page: AI provider, theme, and sound preferences (Sprint 23). */

import {
  AI_PROVIDERS,
  useSettings,
  type AiProviderName,
} from '@/hooks/useSettings'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

const PROVIDER_LABELS: Record<AiProviderName, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  stub: 'Stub (offline)',
}

interface ToggleProps {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}

function Toggle({ label, checked, onChange }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors ${
        checked ? 'bg-primary' : 'bg-input'
      }`}
    >
      <span
        className={`inline-block h-5 w-5 rounded-full bg-background shadow transition-transform ${
          checked ? 'translate-x-5' : 'translate-x-0.5'
        }`}
      />
    </button>
  )
}

function Row({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      {children}
    </div>
  )
}

export default function Settings() {
  const {
    theme,
    aiProvider,
    soundEnabled,
    setTheme,
    setAiProvider,
    setSoundEnabled,
  } = useSettings()

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
      <Card>
        <CardHeader>
          <CardTitle>Preferences</CardTitle>
          <CardDescription>
            Saved locally in this browser; no account data leaves the machine.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-1">
            <label htmlFor="ai-provider" className="text-sm font-medium">
              AI provider
            </label>
            <select
              id="ai-provider"
              value={aiProvider}
              onChange={(event) =>
                setAiProvider(event.target.value as AiProviderName)
              }
              className="flex h-9 w-full max-w-xs rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
            >
              {AI_PROVIDERS.map((provider) => (
                <option key={provider} value={provider}>
                  {PROVIDER_LABELS[provider]}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              Which provider the AI entries come from when the backend allows
              it.
            </p>
          </div>

          <hr className="border-border" />

          <Row
            title="Dark mode"
            description="Switch between the light and dark theme."
          >
            <Toggle
              label="Dark mode"
              checked={theme === 'dark'}
              onChange={(checked) => setTheme(checked ? 'dark' : 'light')}
            />
          </Row>

          <Row title="Sound effects" description="Play sounds during rounds.">
            <Toggle
              label="Sound effects"
              checked={soundEnabled}
              onChange={setSoundEnabled}
            />
          </Row>
        </CardContent>
      </Card>
    </div>
  )
}
