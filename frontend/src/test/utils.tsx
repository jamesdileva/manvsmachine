import { render, type RenderOptions } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'

import { AuthProvider } from '@/contexts/AuthContext'
import { ScoringProvider } from '@/contexts/ScoringContext'
import { VotingProvider } from '@/contexts/VotingContext'

interface Options extends Omit<RenderOptions, 'wrapper'> {
  route?: string
  socketFactory?: Parameters<typeof VotingProvider>[0]['socketFactory']
}

/** Render with the full provider stack (auth + voting + scoring) at a route. */
export function renderWithProviders(ui: ReactElement, options: Options = {}) {
  const { route = '/', socketFactory, ...rest } = options

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          <VotingProvider socketFactory={socketFactory}>
            <ScoringProvider>{children}</ScoringProvider>
          </VotingProvider>
        </AuthProvider>
      </MemoryRouter>
    )
  }

  return render(ui, { wrapper: Wrapper, ...rest })
}
