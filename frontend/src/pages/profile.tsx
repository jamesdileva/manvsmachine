/** Profile page: player stats, streaks, humanity meters + trend (Sprint 22). */

import { useEffect, useRef, useState } from 'react'
import { Chart } from 'chart.js'

import { profileApi } from '@/api/profile'
import { toApiError } from '@/api/errors'
import { HumanityMeter } from '@/components/HumanityMeter'
import { StreakBadge } from '@/components/StreakBadge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { ProfileResponse } from '@/types'

export default function Profile() {
  const [profile, setProfile] = useState<ProfileResponse | null>(null)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    void (async () => {
      try {
        const loaded = await profileApi.get()
        setProfile(loaded)
        setName(loaded.display_name)
      } catch (caught) {
        setError(toApiError(caught).message)
      }
    })()
  }, [])

  // Humanity score trend over the recent entries (Implementation Guide §2.5).
  const recent = profile?.recent_humanity_scores ?? []
  useEffect(() => {
    if (!canvasRef.current || recent.length === 0) return
    const chart = new Chart(canvasRef.current, {
      type: 'line',
      data: {
        labels: recent.map((entry) => entry.date),
        datasets: [
          {
            label: 'Humanity score',
            data: recent.map((entry) => entry.score),
            borderColor: 'hsl(var(--primary))',
            backgroundColor: 'hsl(var(--primary))',
            tension: 0.3,
          },
        ],
      },
      options: {
        scales: {
          y: { min: 0, max: 100, title: { display: true, text: 'Humanity' } },
        },
      },
    })
    return () => chart.destroy()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile])

  async function saveName() {
    setIsSaving(true)
    setSaveError(null)
    try {
      setProfile(await profileApi.update({ display_name: name }))
    } catch (caught) {
      setSaveError(toApiError(caught).message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
        {profile && <StreakBadge days={profile.current_streak} />}
      </div>
      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : !profile ? (
        <p className="text-sm text-muted-foreground">Loading your profile…</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader>
                <CardDescription>Detection Rating</CardDescription>
                <CardTitle data-testid="profile-rating">
                  {profile.detection_rating}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Rounds played</CardDescription>
                <CardTitle data-testid="profile-rounds">
                  {profile.total_rounds}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Overall accuracy</CardDescription>
                <CardTitle data-testid="profile-accuracy">
                  {profile.overall_accuracy.toFixed(1)}%
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Streaks</CardTitle>
            </CardHeader>
            <CardContent className="flex gap-8">
              <div>
                <p
                  className="text-2xl font-bold"
                  data-testid="profile-current-streak"
                >
                  {profile.current_streak}
                </p>
                <p className="text-sm text-muted-foreground">Current</p>
              </div>
              <div>
                <p
                  className="text-2xl font-bold"
                  data-testid="profile-longest-streak"
                >
                  {profile.longest_streak}
                </p>
                <p className="text-sm text-muted-foreground">Longest</p>
              </div>
              <div>
                <p
                  className="text-2xl font-bold"
                  data-testid="profile-daily-streak"
                >
                  {profile.daily_challenge_streak}
                </p>
                <p className="text-sm text-muted-foreground">Daily challenge</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Display name</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-2">
              <Input
                aria-label="Display name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="max-w-xs"
              />
              <Button
                onClick={saveName}
                disabled={isSaving || name === profile.display_name}
              >
                {isSaving ? 'Saving…' : 'Save'}
              </Button>
              {saveError && (
                <span className="text-sm text-destructive">{saveError}</span>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent humanity scores</CardTitle>
              <CardDescription>
                How human-like your recent entries read, 0-100.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recent.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Play a round to earn your first humanity score.
                </p>
              ) : (
                recent.map((entry) => (
                  <div key={entry.challenge_id} className="space-y-1">
                    <div className="flex justify-between text-sm text-muted-foreground">
                      <span>{entry.challenge_id}</span>
                      <span>{entry.date}</span>
                    </div>
                    <HumanityMeter
                      score={entry.score}
                      label={entry.challenge_id}
                    />
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {recent.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Humanity trend</CardTitle>
              </CardHeader>
              <CardContent>
                <canvas data-testid="humanity-trend" ref={canvasRef} />
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
