import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export default function Profile() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
      <Card>
        <CardHeader>
          <CardTitle>Your stats</CardTitle>
          <CardDescription>
            Detection Rating, accuracy, streaks, and your humanity trend appear
            here.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </div>
  )
}
