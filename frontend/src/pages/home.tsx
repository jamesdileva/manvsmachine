import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useNavigate } from 'react-router-dom'

export default function Home() {
  const navigate = useNavigate()
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Man vs. Machine</h1>
      <Card>
        <CardHeader>
          <CardTitle>Can you spot the machine?</CardTitle>
          <CardDescription>
            Write a micro-challenge entry against the clock, then guess which of
            two anonymized entries was written by the AI.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => navigate('/session')}>
            Play the daily challenge
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
