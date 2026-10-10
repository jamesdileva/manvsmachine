import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from '@/contexts/AuthContext'
import { ScoringProvider } from '@/contexts/ScoringContext'
import { VotingProvider } from '@/contexts/VotingContext'
import { AppRoutes } from '@/routes'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <VotingProvider>
          <ScoringProvider>
            <AppRoutes />
          </ScoringProvider>
        </VotingProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
