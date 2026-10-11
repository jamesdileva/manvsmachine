/** ShareButton: fetch a result card, then copy the text or download the image (Sprint 25). */

import { useState } from 'react'
import { Download, Link2, Share2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useShare } from '@/hooks/useShare'
import { cn } from '@/lib/utils'

interface ShareButtonProps {
  sessionId: string
  className?: string
}

export function ShareButton({ sessionId, className }: ShareButtonProps) {
  const { share, copyText, downloadImage, isSharing, error, copied, result } =
    useShare()
  const [open, setOpen] = useState(false)

  async function openShare() {
    setOpen(true)
    await share(sessionId)
  }

  return (
    <div className={cn('relative', className)}>
      <Button onClick={openShare} disabled={isSharing}>
        <Share2 className="mr-1.5 h-4 w-4" aria-hidden />
        {isSharing ? 'Sharing…' : 'Share'}
      </Button>

      {open && (
        <div
          className="absolute right-0 top-11 z-10 w-72 space-y-3 rounded-md border bg-card p-4 shadow-md"
          data-testid="share-dialog"
          role="dialog"
          aria-label="Share this result"
        >
          {error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : (
            <>
              <p
                className="text-sm text-muted-foreground"
                data-testid="share-text"
              >
                {result?.share_text ?? 'Preparing your result…'}
              </p>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="secondary" onClick={copyText}>
                  <Link2 className="mr-1.5 h-4 w-4" aria-hidden />
                  Copy
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={downloadImage}
                  disabled={!result?.share_image}
                >
                  <Download className="mr-1.5 h-4 w-4" aria-hidden />
                  Download
                </Button>
                {copied && (
                  <span className="text-xs text-muted-foreground">Copied!</span>
                )}
              </div>
              <a
                href={result?.share_url ?? '#'}
                className="block text-xs text-muted-foreground underline"
                data-testid="share-link"
              >
                {result?.share_url ?? ''}
              </a>
            </>
          )}
        </div>
      )}
    </div>
  )
}
