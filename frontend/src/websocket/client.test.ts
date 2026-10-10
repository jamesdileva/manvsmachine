import { describe, expect, it, vi } from 'vitest'

import {
  SessionSocket,
  toWebSocketUrl,
  type SocketLike,
} from '@/websocket/client'
import { ServerEvent } from '@/websocket/events'

class FakeSocket implements SocketLike {
  sent: string[] = []
  closed = false
  onopen: ((event: unknown) => void) | null = null
  onmessage: ((event: { data: unknown }) => void) | null = null
  onclose: ((event: { code: number; reason?: string }) => void) | null = null
  onerror: ((event: unknown) => void) | null = null

  send(data: string): void {
    this.sent.push(data)
  }
  close(): void {
    this.closed = true
  }

  // test helpers
  fireOpen() {
    this.onopen?.({})
  }
  fireMessage(payload: unknown) {
    this.onmessage?.({
      data: typeof payload === 'string' ? payload : JSON.stringify(payload),
    })
  }
  fireClose(code = 1000, reason?: string) {
    this.onclose?.({ code, reason })
  }
}

function setup() {
  const socket = new FakeSocket()
  const factory = vi.fn(() => socket as unknown as WebSocket)
  const onMessage = vi.fn()
  const onOpen = vi.fn()
  const onClose = vi.fn()
  const onError = vi.fn()
  const client = new SessionSocket(
    'ws://test/ws/session/s1',
    { onMessage, onOpen, onClose, onError },
    factory,
  )
  return { client, socket, factory, onMessage, onOpen, onClose, onError }
}

describe('SessionSocket', () => {
  it('connects with the factory and wires handlers', () => {
    const { client, socket, factory, onOpen } = setup()
    client.connect()
    expect(factory).toHaveBeenCalledWith('ws://test/ws/session/s1')
    socket.fireOpen()
    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  it('parses and dispatches server events', () => {
    const { client, socket, onMessage } = setup()
    client.connect()
    socket.fireMessage({
      type: ServerEvent.ROUND_START,
      data: { roundNumber: 1 },
    })
    expect(onMessage).toHaveBeenCalledWith({
      type: 'ROUND_START',
      data: { roundNumber: 1 },
    })
  })

  it('reports malformed payloads through onError', () => {
    const { client, socket, onMessage, onError } = setup()
    client.connect()
    socket.fireMessage('not json')
    expect(onMessage).not.toHaveBeenCalled()
    expect(onError).toHaveBeenCalledTimes(1)

    socket.fireMessage(JSON.stringify({ noType: true }))
    expect(onError).toHaveBeenCalledTimes(2)
  })

  it('sends typed client events', () => {
    const { client, socket } = setup()
    client.connect()
    client.submitEntry('r1', 'Fire baked. Dragon approved.', 's1')
    client.vote('r1', 'A', 's1')
    client.ping()

    const parsed = socket.sent.map((raw) => JSON.parse(raw))
    expect(parsed[0]).toEqual({
      type: 'SUBMIT_ENTRY',
      data: {
        roundId: 'r1',
        entry: 'Fire baked. Dragon approved.',
        sessionId: 's1',
      },
    })
    expect(parsed[1]).toEqual({
      type: 'VOTE',
      data: { roundId: 'r1', vote: 'A', sessionId: 's1' },
    })
    expect(parsed[2]).toEqual({ type: 'PING', data: {} })
  })

  it('forwards close events and clears the socket', () => {
    const { client, socket, onClose } = setup()
    client.connect()
    socket.fireClose(1006, 'dropped')
    expect(onClose).toHaveBeenCalledWith({ code: 1006, reason: 'dropped' })

    // Sending after close is a no-op rather than a crash.
    client.vote('r1', 'A')
    expect(socket.sent).toHaveLength(0)
  })

  it('closes on request', () => {
    const { client, socket } = setup()
    client.connect()
    client.close()
    expect(socket.closed).toBe(true)
  })
})

describe('toWebSocketUrl', () => {
  it('converts the API base into a socket url', () => {
    expect(toWebSocketUrl('http://127.0.0.1:8000/api/v1', 's1', 'a.b.c')).toBe(
      'ws://127.0.0.1:8000/ws/session/s1?token=a.b.c',
    )
  })

  it('encodes the token and handles https bases', () => {
    expect(toWebSocketUrl('https://example.com/api/v1', 's1', 'a b+c')).toBe(
      'wss://example.com/ws/session/s1?token=a%20b%2Bc',
    )
  })
})
