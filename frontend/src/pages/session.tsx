import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export default function Session() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Session</h1>
      <Card>
        <CardHeader>
          <CardTitle>No active session</CardTitle>
          <CardDescription>
            The 3-round game loop (challenge → write → vote → reveal → score) is
            wired up here once the session flow lands.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </div>
  )
}
