import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { URGENT_THRESHOLD, useTimer } from '@/hooks/useTimer'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useTimer', () => {
  it('counts down from the started value', () => {
    const { result } = renderHook(() => useTimer())
    expect(result.current.secondsLeft).toBe(0)

    act(() => result.current.start(15))
    expect(result.current.secondsLeft).toBe(15)
    expect(result.current.isRunning).toBe(true)

    act(() => {
      vi.advanceTimersByTime(5_000)
    })
    expect(result.current.secondsLeft).toBe(10)
  })

  it('flags the urgency window', () => {
    const { result } = renderHook(() => useTimer())
    act(() => result.current.start(10))
    expect(result.current.isUrgent).toBe(false)

    act(() => {
      vi.advanceTimersByTime(6_000)
    })
    expect(result.current.secondsLeft).toBe(4)
    expect(result.current.isUrgent).toBe(true)
    expect(result.current.secondsLeft).toBeLessThanOrEqual(URGENT_THRESHOLD)
  })

  it('fires the expiry callback once at zero', () => {
    const onExpire = vi.fn()
    const { result } = renderHook(() => useTimer(onExpire))

    act(() => result.current.start(2))
    act(() => {
      vi.advanceTimersByTime(2_500)
    })
    expect(result.current.secondsLeft).toBe(0)
    expect(result.current.isRunning).toBe(false)
    expect(result.current.isExpired).toBe(true)
    expect(onExpire).toHaveBeenCalledTimes(1)

    act(() => {
      vi.advanceTimersByTime(5_000)
    })
    expect(onExpire).toHaveBeenCalledTimes(1)
  })

  it('stops and resets', () => {
    const { result } = renderHook(() => useTimer())
    act(() => result.current.start(15))
    act(() => {
      vi.advanceTimersByTime(3_000)
    })
    act(() => result.current.stop())
    expect(result.current.isRunning).toBe(false)

    act(() => {
      vi.advanceTimersByTime(2_000)
    })
    expect(result.current.secondsLeft).toBe(12) // frozen while stopped

    act(() => result.current.reset(20))
    expect(result.current.secondsLeft).toBe(20)
    expect(result.current.isRunning).toBe(false)
    expect(result.current.isExpired).toBe(false)
  })
})
