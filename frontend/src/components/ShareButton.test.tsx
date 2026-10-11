import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'

import { apiClient } from '@/api/client'
import { ShareButton } from '@/components/ShareButton'
import type { ShareResponse } from '@/types'

let mock: MockAdapter

const shareResponse: ShareResponse = {
  share_text: 'I scored 275 on today’s Man vs. Machine daily challenge!',
  share_url: '/s/s1',
  share_image: 'iVBORw0KGgo=',
}

beforeEach(() => {
  mock = new MockAdapter(apiClient)
  vi.restoreAllMocks()
})

describe('ShareButton', () => {
  it('renders the share trigger before anything is shared', () => {
    render(<ShareButton sessionId="s1" />)
    expect(screen.getByRole('button', { name: /share/i })).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /copy/i }),
    ).not.toBeInTheDocument()
  })

  it('fetches the result and reveals the copy/download actions', async () => {
    mock.onPost('/share/result').reply(200, shareResponse)
    render(<ShareButton sessionId="s1" />)

    await userEvent.click(screen.getByRole('button', { name: /share/i }))

    expect(
      await screen.findByRole('button', { name: /copy/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /download/i }),
    ).toBeInTheDocument()
    expect(screen.getByTestId('share-link')).toHaveAttribute(
      'href',
      expect.stringContaining('/s/s1'),
    )
  })

  it('copies the text to the clipboard', async () => {
    mock.onPost('/share/result').reply(200, shareResponse)
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    render(<ShareButton sessionId="s1" />)

    await userEvent.click(screen.getByRole('button', { name: /share/i }))
    await userEvent.click(await screen.findByRole('button', { name: /copy/i }))

    expect(writeText).toHaveBeenCalledWith(shareResponse.share_text)
    expect(await screen.findByText(/copied/i)).toBeInTheDocument()
  })

  it('shows an error when the share request fails', async () => {
    mock.onPost('/share/result').reply(404, { detail: 'session not found' })
    render(<ShareButton sessionId="s1" />)

    await userEvent.click(screen.getByRole('button', { name: /share/i }))

    expect(await screen.findByText(/session not found/i)).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /copy/i }),
    ).not.toBeInTheDocument()
  })
})
