import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'

export default function Auth() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Sign in</h1>
      <Card className="max-w-sm">
        <CardHeader>
          <CardTitle>Player account</CardTitle>
          <CardDescription>
            Play as a guest instantly, or sign in to keep your Detection Rating
            across sessions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            type="email"
            placeholder="you@example.com"
            aria-label="Email"
          />
          <Input type="password" placeholder="Password" aria-label="Password" />
          <div className="flex gap-2">
            <Button>Sign in</Button>
            <Button variant="outline">Continue as guest</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
