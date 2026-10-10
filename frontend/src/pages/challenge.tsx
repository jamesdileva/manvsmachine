import { useEffect, useState } from 'react'

import { ChallengeView } from '@/components/ChallengeView'
import { EntryInput } from '@/components/EntryInput'
import { Timer } from '@/components/Timer'
import { useChallenges } from '@/hooks/useChallenges'
import { useTimer } from '@/hooks/useTimer'
import { toApiError } from '@/api/errors'
import { votingApi } from '@/api/voting'
import type { SubmitEntryResponse } from '@/types'

export default function Challenge() {
  const { daily, challenge, isLoading, error, loadDaily, validateEntry } =
    useChallenges()
  const [entry, setEntry] = useState('')
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult] = useState<SubmitEntryResponse | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const timer = useTimer()

  useEffect(() => {
    void loadDaily()
  }, [loadDaily])

  const challengeId = challenge?.id
  useEffect(() => {
    if (challengeId) timer.start(challenge?.timeLimitSeconds ?? 15)
    // The timer restarts per challenge (Sprint 21 drives this from the session).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [challengeId])

  async function handleSubmit(value: string) {
    if (!challenge) return
    setSubmitError(null)
    setSubmitting(true)
    timer.stop()
    try {
      const validation = await validateEntry(challenge.id, value)
      if (validation && !validation.valid) {
        setSubmitError(validation.hard_violations.join('; '))
        return
      }
      setResult(
        await votingApi.submitEntry({
          challenge_id: challenge.id,
          entry: value,
        }),
      )
    } catch (caught) {
      setSubmitError(toApiError(caught).message)
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading && !challenge) {
    return (
      <p className="text-muted-foreground">Loading today&apos;s challenge…</p>
    )
  }

  if (error) {
    return <p className="text-destructive">{error}</p>
  }

  if (!challenge || !daily) {
    return <p className="text-muted-foreground">No challenge available.</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Challenge</h1>
      <ChallengeView challenge={challenge}>
        <Timer
          secondsLeft={timer.secondsLeft}
          totalSeconds={challenge.timeLimitSeconds}
          isRunning={timer.isRunning}
        />
        <EntryInput
          challenge={challenge}
          value={entry}
          onChange={setEntry}
          onSubmit={handleSubmit}
          disabled={timer.isExpired || result !== null}
          submitting={submitting}
        />
      </ChallengeView>

      {submitError && (
        <p role="alert" className="text-sm text-destructive">
          {submitError}
        </p>
      )}

      {result && (
        <div className="space-y-2" data-testid="practice-result">
          <h2 className="text-lg font-semibold">Practice result</h2>
          <p>
            <span className="text-muted-foreground">You: </span>
            {result.human_entry}
          </p>
          <p>
            <span className="text-muted-foreground">
              AI ({result.provider}/{result.model}):{' '}
            </span>
            {result.ai_entry}
          </p>
        </div>
      )}
    </div>
  )
}
