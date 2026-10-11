import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { apiClient } from '@/api/client'
import { useShare } from '@/hooks/useShare'
import type { ShareResponse } from '@/types'

let mock: MockAdapter

// A 1x1 transparent PNG, base64 encoded.
const PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='

const shareResponse: ShareResponse = {
  share_text:
    "I scored 275 on today's Man vs. Machine daily challenge! Can you beat my accuracy? #ManVsMachine",
  share_url: '/s/s1',
  share_image: PNG_BASE64,
}

beforeEach(() => {
  mock = new MockAdapter(apiClient)
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('useShare', () => {
  it('posts the share result and keeps the text and link', async () => {
    mock.onPost('/share/result').reply(200, shareResponse)
    const { result } = renderHook(() => useShare())

    await act(async () => {
      await result.current.share('s1')
    })

    expect(result.current.result?.share_url).toBe('/s/s1')
    expect(result.current.isSharing).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('requests the text-only format when asked', async () => {
    mock
      .onPost('/share/result')
      .reply(200, { ...shareResponse, share_image: null })
    const { result } = renderHook(() => useShare())

    await act(async () => {
      await result.current.share('s1', 'text')
    })

    expect(JSON.parse(mock.history.post[0].data)).toEqual({
      session_id: 's1',
      format: 'text',
    })
    expect(result.current.result?.share_image).toBeNull()
  })

  it('surfaces errors from the share endpoint', async () => {
    mock.onPost('/share/result').reply(404, { detail: 'session not found' })
    const { result } = renderHook(() => useShare())

    await act(async () => {
      await result.current.share('nope')
    })

    expect(result.current.error).toBe('session not found')
    expect(result.current.result).toBeNull()
  })

  it('copies the share text to the clipboard', async () => {
    mock.onPost('/share/result').reply(200, shareResponse)
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    const { result } = renderHook(() => useShare())

    await act(async () => {
      await result.current.share('s1')
    })
    await act(async () => {
      await result.current.copyText()
    })

    expect(writeText).toHaveBeenCalledWith(shareResponse.share_text)
    expect(result.current.copied).toBe(true)
  })

  it('downloads the card as a PNG file', async () => {
    mock.onPost('/share/result').reply(200, shareResponse)
    const clicks: HTMLAnchorElement[] = []
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(function (this: HTMLAnchorElement) {
        clicks.push(this)
      })
    const { result } = renderHook(() => useShare())

    await act(async () => {
      await result.current.share('s1')
    })
    act(() => {
      result.current.downloadImage()
    })

    expect(click).toHaveBeenCalled()
    expect(clicks[0].getAttribute('href')).toBe(
      `data:image/png;base64,${PNG_BASE64}`,
    )
    expect(clicks[0].getAttribute('download')).toBe('manvs-machine-result.png')
  })
})
