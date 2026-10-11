/** useShare: generate, copy, and download shareable results (Sprint 25). */

import { useCallback, useState } from 'react'

import { shareApi } from '@/api/share'
import { toApiError } from '@/api/errors'
import type { ShareFormat, ShareResponse } from '@/types'

const IMAGE_FILENAME = 'manvs-machine-result.png'

export interface UseShare {
  /** The generated result, once shared. */
  result: ShareResponse | null
  isSharing: boolean
  error: string | null
  /** True right after a successful clipboard copy (resets on the next share). */
  copied: boolean
  share: (sessionId: string, format?: ShareFormat) => Promise<void>
  copyText: () => Promise<void>
  downloadImage: () => void
}

export function useShare(): UseShare {
  const [result, setResult] = useState<ShareResponse | null>(null)
  const [isSharing, setIsSharing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const share = useCallback(
    async (sessionId: string, format: ShareFormat = 'image') => {
      setIsSharing(true)
      setError(null)
      setCopied(false)
      try {
        setResult(await shareApi.result({ session_id: sessionId, format }))
      } catch (caught) {
        setError(toApiError(caught).message)
        setResult(null)
      } finally {
        setIsSharing(false)
      }
    },
    [],
  )

  const copyText = useCallback(async () => {
    if (!result) return
    await navigator.clipboard.writeText(result.share_text)
    setCopied(true)
  }, [result])

  const downloadImage = useCallback(() => {
    if (!result?.share_image) return
    const link = document.createElement('a')
    link.href = `data:image/png;base64,${result.share_image}`
    link.download = IMAGE_FILENAME
    link.click()
  }, [result])

  return { result, isSharing, error, copied, share, copyText, downloadImage }
}
