/** Share types — mirror the backend schemas (Implementation Guide §2.6; Sprint 25). */

export type ShareFormat = 'image' | 'text'

export interface ShareRequest {
  session_id: string
  format?: ShareFormat
  /** The player's own words; echoed onto the card. */
  message?: string
}

export interface ShareResponse {
  share_text: string
  share_url: string
  /** Base64 PNG result card; null for the text-only format. */
  share_image?: string | null
}
