/** Share types — mirror the backend schemas (Implementation Guide §2.6; Sprint 25). */

export interface ShareRequest {
  session_id: string
  format?: 'image' | 'text'
  message?: string
}

export interface ShareResponse {
  share_text: string
  share_url: string
}
