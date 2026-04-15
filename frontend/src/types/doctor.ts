export type DoctorClinicBucket =
  | 'novosibirsk'
  | 'kemerovo'
  | 'yaroslavl'
  | 'test'

export interface DoctorMeResponse {
  id: number
  username: string
  can_view_test_tab: boolean
  allowed_clinic_bucket: DoctorClinicBucket | null
  has_strict_doctor_name_filter: boolean
}

export interface DoctorAuthResponse {
  access_token: string
  token_type: string
  doctor: DoctorMeResponse
}

export interface DoctorSessionItem {
  session_id: string
  patient_name?: string
  doctor_name?: string
  appointment_at?: string
  start_time?: string
  end_time?: string
  duration_minutes?: number
  preview_url: string
  download_url: string
  share_url: string
}

export interface DoctorSessionsResponse {
  items: DoctorSessionItem[]
  total: number
}

export interface DoctorPdfShareResponse {
  share_url: string
  expires_in_hours: number
}

export type DoctorSessionSortField =
  | 'patient_name'
  | 'doctor_name'
  | 'appointment_at'
  | 'start_time'
  | 'end_time'
  | 'duration_minutes'

export type DoctorSessionSortOrder = 'asc' | 'desc'

export interface DoctorFilters {
  doctorName: string
  dateFrom: string
  dateTo: string
}
