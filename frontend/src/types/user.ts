/** Auth and profile types — mirror the backend schemas (Implementation Guide §2.1/§2.5). */

export interface GuestAuthRequest {
  /** Resume an existing guest when provided, else a new one is issued. */
  guest_id?: string | null
  display_name?: string | null
}

export interface RegisterRequest {
  email: string
  password: string
  display_name: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AuthResponse {
  user_id: string
  guest_id: string | null
  display_name: string
  is_guest: boolean
  token: string
}

export interface MeResponse {
  user_id: string
  guest_id: string | null
  display_name: string
  is_guest: boolean
}

export interface RecentHumanityScore {
  challenge_id: string
  score: number
  date: string
}

/** `GET /profile` response (Implementation Guide §2.5; endpoint lands in Sprint 22). */
export interface ProfileResponse {
  user_id: string
  display_name: string
  is_guest: boolean
  detection_rating: number
  total_rounds: number
  overall_accuracy: number
  current_streak: number
  longest_streak: number
  daily_challenge_streak: number
  recent_humanity_scores: RecentHumanityScore[]
}

export interface ProfileUpdateRequest {
  display_name: string
}
