import { AlertTriangle, Send } from 'lucide-react'
import { useId } from 'react'

import { Button } from '@/components/ui/button'
import { checkEntry, countWords } from '@/lib/constraints'
import { cn } from '@/lib/utils'
import type { ChallengeDefinition } from '@/types'

interface EntryInputProps {
  challenge: ChallengeDefinition
  value: string
  onChange: (value: string) => void
  onSubmit: (entry: string) => void
  /** Disables the controls (AI generation in flight, round scored, ...). */
  disabled?: boolean
  submitting?: boolean
  className?: string
}

export function EntryInput({
  challenge,
  value,
  onChange,
  onSubmit,
  disabled = false,
  submitting = false,
  className,
}: EntryInputProps) {
  const words = countWords(value)
  const characters = value.length
  const check = checkEntry(value, challenge.constraints)
  const inputId = useId()
  const singleLine = challenge.inputType === 'text_single_line'
  const wordLimit = challenge.constraints.find(
    (c) => c.type === 'max_words',
  )?.value
  const charLimit = challenge.constraints.find(
    (c) => c.type === 'max_characters',
  )?.value

  return (
    <form
      className={cn('space-y-2', className)}
      data-testid="entry-input"
      onSubmit={(event) => {
        event.preventDefault()
        if (!disabled && !submitting && check.valid) onSubmit(value)
      }}
    >
      <label htmlFor={inputId} className="sr-only">
        Your entry
      </label>
      {singleLine ? (
        <input
          id={inputId}
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled || submitting}
          placeholder="Write your entry…"
        />
      ) : (
        <textarea
          id={inputId}
          className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled || submitting}
          placeholder="Write your entry…"
        />
      )}

      <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
        <span data-testid="entry-counts">
          {words} word{words === 1 ? '' : 's'}
          {wordLimit !== undefined && ` / ${wordLimit}`} · {characters} char
          {charLimit !== undefined && ` / ${charLimit}`}
        </span>
        <Button
          type="submit"
          size="sm"
          disabled={disabled || submitting || !check.valid}
        >
          <Send className="h-3.5 w-3.5" aria-hidden />
          {submitting ? 'Submitting…' : 'Submit'}
        </Button>
      </div>

      {check.valid ? (
        check.softViolations.length > 0 && (
          <p
            className="text-xs text-muted-foreground"
            data-testid="soft-violations"
          >
            Bonus constraint unmet: {check.softViolations.join('; ')}
          </p>
        )
      ) : (
        <p
          className="flex items-center gap-1.5 text-xs text-destructive"
          role="alert"
          data-testid="hard-violations"
        >
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
          {check.hardViolations.join('; ')}
        </p>
      )}
    </form>
  )
}
