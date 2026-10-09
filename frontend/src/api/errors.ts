/** Typed error shape for failed API calls (401/404/500 handling). */

import axios from 'axios'

export interface ApiError {
  /** HTTP status, or 0 for a network/offline failure. */
  status: number
  message: string
  /** The backend's `detail` payload (string, or an object like `{hard_violations: [...]}`). */
  details?: unknown
}

/** Normalize any thrown value into an `ApiError` components can render. */
export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0
    const detail = (error.response?.data as { detail?: unknown } | undefined)
      ?.detail
    let message = error.message
    if (typeof detail === 'string') {
      message = detail
    } else if (detail && typeof detail === 'object') {
      const violations = (detail as { hard_violations?: string[] })
        .hard_violations
      message = violations?.length
        ? violations.join('; ')
        : JSON.stringify(detail)
    }
    return { status, message, details: detail }
  }
  if (error instanceof Error) {
    return { status: 0, message: error.message }
  }
  return { status: 0, message: 'Unexpected error' }
}
