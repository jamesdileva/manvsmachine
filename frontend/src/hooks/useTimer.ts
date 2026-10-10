/**
 * useTimer: countdown with urgency states and an expiry callback.
 *
 * Ticks against a deadline (not a decrementing counter) so the display stays
 * accurate even if an interval tick is delayed.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

/** Seconds left at or below this are "urgent" (the UI turns red). */
export const URGENT_THRESHOLD = 5

export interface UseTimer {
  secondsLeft: number
  isRunning: boolean
  /** True when the clock is inside the urgency window. */
  isUrgent: boolean
  isExpired: boolean
  start: (seconds?: number) => void
  stop: () => void
  reset: (seconds?: number) => void
}

export function useTimer(onExpire?: () => void): UseTimer {
  const [secondsLeft, setSecondsLeft] = useState(0)
  const [isRunning, setIsRunning] = useState(false)
  const deadlineRef = useRef<number | null>(null)
  const expiredRef = useRef(false)
  const onExpireRef = useRef(onExpire)
  onExpireRef.current = onExpire

  const stop = useCallback(() => {
    deadlineRef.current = null
    setIsRunning(false)
  }, [])

  const reset = useCallback((seconds = 0) => {
    deadlineRef.current = null
    expiredRef.current = false
    setIsRunning(false)
    setSecondsLeft(seconds)
  }, [])

  const start = useCallback((seconds = 0) => {
    expiredRef.current = false
    deadlineRef.current = Date.now() + seconds * 1000
    setSecondsLeft(seconds)
    setIsRunning(true)
  }, [])

  useEffect(() => {
    if (!isRunning) return
    const tick = () => {
      const deadline = deadlineRef.current
      if (deadline === null) return
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000))
      setSecondsLeft(remaining)
      if (remaining <= 0) {
        expiredRef.current = true
        stop()
        onExpireRef.current?.()
      }
    }
    tick()
    const interval = setInterval(tick, 250)
    return () => clearInterval(interval)
  }, [isRunning, stop])

  return {
    secondsLeft,
    isRunning,
    isUrgent: isRunning && secondsLeft > 0 && secondsLeft <= URGENT_THRESHOLD,
    isExpired: expiredRef.current,
    start,
    stop,
    reset,
  }
}
