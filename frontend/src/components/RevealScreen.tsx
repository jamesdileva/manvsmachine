import { Check, X } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { RevealPayload } from '@/websocket/events'

interface RevealScreenProps {
  reveal: RevealPayload
  className?: string
}

/** 0-100 humanity bar. */
function HumanityBar({ label, value }: { label: string; value: number }) {
  const percent = Math.max(0, Math.min(100, value))
  return (
    <div className="space-y-1" data-testid={`humanity-${label.toLowerCase()}`}>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span className="tabular-nums">{Math.round(percent)}</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-secondary"
        role="progressbar"
        aria-label={`${label} humanity score`}
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

export function RevealScreen({ reveal, className }: RevealScreenProps) {
  return (
    <Card className={className} data-testid="reveal-screen">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {reveal.voteCorrect ? (
            <Badge>
              <Check className="mr-1 h-3.5 w-3.5" aria-hidden />
              Correct
            </Badge>
          ) : (
            <Badge variant="destructive">
              <X className="mr-1 h-3.5 w-3.5" aria-hidden />
              Fooled
            </Badge>
          )}
          Entry {reveal.humanWas} was human · Entry {reveal.aiWas} was the AI
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {reveal.entries && (
          <div className="grid gap-3 sm:grid-cols-2">
            {[reveal.humanWas, reveal.aiWas].map((letter) => {
              const isHuman = letter === reveal.humanWas
              return (
                <div
                  key={letter}
                  className="rounded-md border p-3 text-sm"
                  data-testid={`revealed-entry-${letter}`}
                >
                  <p className="mb-1 text-xs font-semibold text-muted-foreground">
                    Entry {letter} — {isHuman ? 'yours' : 'the AI'}
                  </p>
                  <p className="whitespace-pre-wrap">
                    {reveal.entries?.[letter]}
                  </p>
                </div>
              )
            })}
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <HumanityBar label="Your entry" value={reveal.humanityHuman} />
          <HumanityBar label="AI entry" value={reveal.humanityAI} />
        </div>

        <p
          className="text-sm text-muted-foreground"
          data-testid="reveal-explanation"
        >
          {reveal.explanation}
        </p>
      </CardContent>
    </Card>
  )
}
