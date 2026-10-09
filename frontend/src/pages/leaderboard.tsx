import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export default function Leaderboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Leaderboard</h1>
      <Card>
        <CardHeader>
          <CardTitle>Daily and all-time rankings</CardTitle>
          <CardDescription>
            Ranks by score and by Detection Rating appear here once the profile
            data is wired up.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </div>
  )
}
