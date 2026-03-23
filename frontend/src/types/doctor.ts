export interface DoctorMeResponse {
  id: number
  username: string
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
  start_time?: string
  end_time?: string
  duration_minutes?: number
  preview_url: string
  download_url: string
}

export interface DoctorSessionsResponse {
  items: DoctorSessionItem[]
  total: number
}

export interface DoctorFilters {
  doctorName: string
  dateFrom: string
  dateTo: string
}
