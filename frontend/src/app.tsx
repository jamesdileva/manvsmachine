import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from '@/contexts/AuthContext'
import { ScoringProvider } from '@/contexts/ScoringContext'
import { SessionProvider } from '@/contexts/SessionContext'
import { VotingProvider } from '@/contexts/VotingContext'
import { AppRoutes } from '@/routes'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <VotingProvider>
          <ScoringProvider>
            <SessionProvider>
              <AppRoutes />
            </SessionProvider>
          </ScoringProvider>
        </VotingProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
