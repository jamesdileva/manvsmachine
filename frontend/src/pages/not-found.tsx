import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="space-y-4">
      <p className="text-2xl font-bold tracking-tight">Page not found</p>
      <p className="text-muted-foreground">
        That route does not exist. Head back and try another challenge.
      </p>
      <Button asChild>
        <Link to="/">Back to home</Link>
      </Button>
    </div>
  )
}
