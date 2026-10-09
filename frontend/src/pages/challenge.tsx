import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export default function Challenge() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Challenge</h1>
      <Card>
        <CardHeader>
          <CardTitle>Today&apos;s challenge</CardTitle>
          <CardDescription>
            The challenge prompt, constraints, and timer render here once a
            session is active.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </div>
  )
}
