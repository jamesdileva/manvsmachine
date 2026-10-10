/**
 * WebSocket client wrapper for a session's live channel.
 *
 * Thin on purpose: connect, typed send, JSON dispatch, close. Reconnects are the
 * caller's job (the server keeps authoritative state in SQLite, so a reconnect
 * replays SESSION_STARTED + ROUND_START).
 */

import { ClientEvent, type ServerEventMessage } from '@/websocket/events'

export type WebSocketFactory = (url: string) => WebSocket

/** The slice of the browser WebSocket this client relies on (fakes are fine in tests). */
export interface SocketLike {
  send(data: string): void
  close(): void
  onopen: ((event: unknown) => void) | null
  onmessage: ((event: { data: unknown }) => void) | null
  onclose: ((event: { code: number; reason?: string }) => void) | null
  onerror: ((event: unknown) => void) | null
}

export type ConnectionStatus =
  'idle' | 'connecting' | 'open' | 'closed' | 'error'

export interface SessionSocketHandlers {
  onOpen?: () => void
  onMessage: (message: ServerEventMessage) => void
  onClose?: (event: { code: number; reason?: string }) => void
  onError?: (error: unknown) => void
}

const defaultFactory: WebSocketFactory = (url) => new WebSocket(url)

export class SessionSocket {
  private socket: SocketLike | null = null

  constructor(
    private readonly url: string,
    private readonly handlers: SessionSocketHandlers,
    private readonly factory: WebSocketFactory = defaultFactory,
  ) {}

  connect(): void {
    if (this.socket) return
    const socket = this.factory(this.url) as unknown as SocketLike
    this.socket = socket
    socket.onopen = () => this.handlers.onOpen?.()
    socket.onmessage = (event) => this.handleMessage(event)
    socket.onclose = (event) => {
      this.socket = null
      this.handlers.onClose?.(event)
    }
    socket.onerror = (event) => this.handlers.onError?.(event)
  }

  send(type: string, data: Record<string, unknown>): void {
    this.socket?.send(JSON.stringify({ type, data }))
  }

  submitEntry(roundId: string, entry: string, sessionId?: string): void {
    this.send(ClientEvent.SUBMIT_ENTRY, { roundId, entry, sessionId })
  }

  vote(roundId: string, vote: string, sessionId?: string): void {
    this.send(ClientEvent.VOTE, { roundId, vote, sessionId })
  }

  ping(): void {
    this.send(ClientEvent.PING, {})
  }

  close(): void {
    this.socket?.close()
    this.socket = null
  }

  private handleMessage(event: { data: unknown }): void {
    try {
      const message = JSON.parse(String(event.data)) as ServerEventMessage
      if (message && typeof message.type === 'string') {
        this.handlers.onMessage(message)
      } else {
        this.handlers.onError?.(new Error('malformed event payload'))
      }
    } catch (error) {
      this.handlers.onError?.(error)
    }
  }
}

/** Build the ws(s):// URL for a session channel. */
export function toWebSocketUrl(
  baseUrl: string,
  sessionId: string,
  token: string,
): string {
  const wsBase = baseUrl.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
  return `${wsBase}/ws/session/${sessionId}?token=${encodeURIComponent(token)}`
}
