/**
 * useVoting: the session's live WebSocket channel.
 *
 * Connects on demand (`connect(sessionId)`), dispatches typed server events into
 * state, and exposes typed client actions. Reconnects are the caller's job —
 * the server replays SESSION_STARTED + ROUND_START from SQLite state.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { TOKEN_STORAGE_KEY, API_BASE_URL } from '@/api/client'
import {
  SessionSocket,
  toWebSocketUrl,
  type ConnectionStatus,
  type WebSocketFactory,
} from '@/websocket/client'
import {
  ServerEvent,
  type AiResponseReadyPayload,
  type ErrorPayload,
  type RevealPayload,
  type RoundScoredPayload,
  type RoundStartPayload,
  type ServerEventMessage,
  type SessionEndPayload,
  type SessionStartedPayload,
} from '@/websocket/events'
import type { SessionSummaryResponse } from '@/types'

export type { ConnectionStatus } from '@/websocket/client'

export interface VotingActions {
  connect: (sessionId: string) => void
  disconnect: () => void
  submitEntry: (roundId: string, entry: string) => void
  vote: (roundId: string, letter: string) => void
  ping: () => void
}

export interface VotingState {
  status: ConnectionStatus
  session: SessionStartedPayload | null
  round: RoundStartPayload | null
  /** Anonymized A/B entries, or null while waiting for the AI entry. */
  entries: Record<string, string> | null
  reveal: RevealPayload | null
  score: RoundScoredPayload | null
  summary: SessionSummaryResponse | null
  error: string | null
}

export function useVoting(socketFactory?: WebSocketFactory) {
  const [status, setStatus] = useState<VotingState['status']>('idle')
  const [session, setSession] = useState<SessionStartedPayload | null>(null)
  const [round, setRound] = useState<RoundStartPayload | null>(null)
  const [entries, setEntries] = useState<Record<string, string> | null>(null)
  const [reveal, setReveal] = useState<RevealPayload | null>(null)
  const [score, setScore] = useState<RoundScoredPayload | null>(null)
  const [summary, setSummary] = useState<SessionSummaryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const socketRef = useRef<SessionSocket | null>(null)

  const handleMessage = useCallback((message: ServerEventMessage) => {
    switch (message.type) {
      case ServerEvent.SESSION_STARTED:
        setSession(message.data as SessionStartedPayload)
        setRound(null)
        setEntries(null)
        setReveal(null)
        setScore(null)
        setSummary(null)
        setError(null)
        break
      case ServerEvent.ROUND_START:
        setRound(message.data as RoundStartPayload)
        setEntries(null)
        setReveal(null)
        setScore(null)
        setError(null)
        break
      case ServerEvent.AI_RESPONSE_READY:
        setEntries((message.data as AiResponseReadyPayload).entries)
        break
      case ServerEvent.REVEAL:
        setReveal(message.data as RevealPayload)
        break
      case ServerEvent.ROUND_SCORED:
        setScore(message.data as RoundScoredPayload)
        break
      case ServerEvent.SESSION_END:
        setSummary((message.data as SessionEndPayload).summary)
        break
      case ServerEvent.ERROR:
        setError((message.data as ErrorPayload).message)
        break
      default:
        break
    }
  }, [])

  const connect = useCallback(
    (sessionId: string) => {
      socketRef.current?.close()
      const token = localStorage.getItem(TOKEN_STORAGE_KEY) ?? ''
      const url = toWebSocketUrl(API_BASE_URL, sessionId, token)
      try {
        const socket = new SessionSocket(
          url,
          {
            onOpen: () => setStatus('open'),
            onMessage: handleMessage,
            onClose: () => setStatus('closed'),
            onError: () => setStatus('error'),
          },
          socketFactory,
        )
        socketRef.current = socket
        setStatus('connecting')
        socket.connect()
      } catch {
        // No WebSocket available (blocked, unsupported): report, don't crash.
        socketRef.current = null
        setStatus('error')
      }
    },
    [handleMessage, socketFactory],
  )

  const disconnect = useCallback(() => {
    socketRef.current?.close()
    socketRef.current = null
    setStatus('idle')
  }, [])

  // Close the socket when the consumer unmounts.
  useEffect(() => () => socketRef.current?.close(), [])

  const actions = useMemo<VotingActions>(
    () => ({
      connect,
      disconnect,
      submitEntry: (roundId, entry) =>
        socketRef.current?.submitEntry(roundId, entry),
      vote: (roundId, letter) => socketRef.current?.vote(roundId, letter),
      ping: () => socketRef.current?.ping(),
    }),
    [connect, disconnect],
  )

  const state = useMemo<VotingState>(
    () => ({ status, session, round, entries, reveal, score, summary, error }),
    [status, session, round, entries, reveal, score, summary, error],
  )

  return { ...state, ...actions }
}
