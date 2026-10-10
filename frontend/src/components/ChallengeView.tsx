import { Clock, Gauge, Timer as TimerIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ChallengeDefinition } from '@/types'

const DIFFICULTY_LABEL: Record<number, string> = {
  1: 'Easy',
  2: 'Medium',
  3: 'Hard',
  4: 'Brutal',
}

interface ChallengeViewProps {
  challenge: ChallengeDefinition
  /** Extra content rendered under the prompt (timer, input, ...). */
  children?: React.ReactNode
}

export function ChallengeView({ challenge, children }: ChallengeViewProps) {
  return (
    <Card data-testid="challenge-view">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>{challenge.prompt}</CardTitle>
          <div className="flex shrink-0 items-center gap-2">
            <Badge variant="secondary">
              <Gauge className="mr-1 h-3 w-3" aria-hidden />
              {DIFFICULTY_LABEL[challenge.difficulty] ??
                `Level ${challenge.difficulty}`}
            </Badge>
            <Badge variant="outline">
              <Clock className="mr-1 h-3 w-3" aria-hidden />
              {challenge.timeLimitSeconds}s
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-1" data-testid="constraint-list">
          {challenge.constraints.map((constraint, index) => (
            <li
              key={`${constraint.type}-${index}`}
              className="flex items-center gap-2 text-sm"
            >
              <Badge variant={constraint.isHard ? 'default' : 'outline'}>
                {constraint.isHard ? 'required' : 'bonus'}
              </Badge>
              <span>
                {constraint.description ?? describeConstraint(constraint)}
              </span>
            </li>
          ))}
        </ul>
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <TimerIcon className="h-3 w-3" aria-hidden />
          Vote on which entry is the AI —{' '}
          {challenge.votingCriteria.replace(/_/g, ' ')}.
        </p>
        {children}
      </CardContent>
    </Card>
  )
}

function describeConstraint(
  constraint: ChallengeDefinition['constraints'][number],
): string {
  switch (constraint.type) {
    case 'max_words':
      return `At most ${constraint.value} words`
    case 'max_characters':
      return `At most ${constraint.value} characters`
    case 'must_rhyme':
      return 'Your entry must rhyme'
    case 'no_adjectives':
      return 'No adjectives'
    case 'must_include_theme':
      return `Mention '${constraint.value}'`
    case 'exactly_n_emojis':
      return `Exactly ${constraint.value} emoji(s)`
    case 'no_letter_e':
      return "No letter 'e'"
    case 'one_sentence_only':
      return 'One sentence only'
    default:
      return constraint.type
  }
}
