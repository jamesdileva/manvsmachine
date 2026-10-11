import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from '@/contexts/AuthContext'
import { ScoringProvider } from '@/contexts/ScoringContext'
import { SessionProvider } from '@/contexts/SessionContext'
import { VotingProvider } from '@/contexts/VotingContext'
import { ThemeProvider } from '@/components/ThemeProvider'
import { SettingsProvider } from '@/hooks/useSettings'
import { AppRoutes } from '@/routes'

function App() {
  return (
    <BrowserRouter>
      <SettingsProvider>
        <ThemeProvider>
          <AuthProvider>
            <VotingProvider>
              <ScoringProvider>
                <SessionProvider>
                  <AppRoutes />
                </SessionProvider>
              </ScoringProvider>
            </VotingProvider>
          </AuthProvider>
        </ThemeProvider>
      </SettingsProvider>
    </BrowserRouter>
  )
}

export default App
