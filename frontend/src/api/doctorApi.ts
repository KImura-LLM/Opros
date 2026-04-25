import { useDoctorStore } from '@/store/doctorStore'
import type {
  DoctorAuthResponse,
  DoctorClinicBucket,
  DoctorMeResponse,
  DoctorPdfShareResponse,
  DoctorSessionsResponse,
} from '@/types'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'
const API_BASE_URL = API_URL.replace(/\/api\/v1\/?$/, '')

function getDoctorToken(): string | null {
  try {
    return useDoctorStore.getState().token
  } catch {
    return null
  }
}

async function doctorFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getDoctorToken()
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP error ${response.status}`)
  }

  return response.json() as Promise<T>
}

async function doctorFetchRaw(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getDoctorToken()
  const response = await fetch(resolveDoctorEndpoint(endpoint), {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (!response.ok) {
    let detail = `HTTP error ${response.status}`
    try {
      const errorData = await response.json()
      detail = errorData.detail || detail
    } catch {
      // Тело может быть не JSON, это нормально
    }
    throw new Error(detail)
  }

  return response
}

function resolveDoctorEndpoint(endpoint: string): string {
  if (/^https?:\/\//i.test(endpoint)) {
    return endpoint
  }

  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`

  if (/^https?:\/\//i.test(API_URL)) {
    return `${API_BASE_URL}${normalizedEndpoint}`
  }

  return normalizedEndpoint
}

export async function doctorLogin(
  username: string,
  password: string
): Promise<DoctorAuthResponse> {
  return doctorFetch<DoctorAuthResponse>('/doctors/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export async function getDoctorMe(): Promise<DoctorMeResponse> {
  return doctorFetch<DoctorMeResponse>('/doctors/me')
}

export async function getDoctorSessions(params: {
  clinicBucket: DoctorClinicBucket
  doctorName?: string
  patientName?: string
  dateFrom?: string
  dateTo?: string
}): Promise<DoctorSessionsResponse> {
  const searchParams = new URLSearchParams()

  searchParams.set('clinic_bucket', params.clinicBucket)
  if (params.doctorName) searchParams.set('doctor_name', params.doctorName)
  if (params.patientName) searchParams.set('patient_name', params.patientName)
  if (params.dateFrom) searchParams.set('date_from', params.dateFrom)
  if (params.dateTo) searchParams.set('date_to', params.dateTo)

  const query = searchParams.toString()
  return doctorFetch<DoctorSessionsResponse>(`/doctors/sessions?${query}`)
}

export async function fetchDoctorPreviewHtml(previewUrl: string): Promise<string> {
  const response = await doctorFetchRaw(previewUrl)
  return response.text()
}

export async function fetchDoctorPdf(downloadUrl: string): Promise<{
  blob: Blob
  filename: string
}> {
  const response = await doctorFetchRaw(downloadUrl)
  const blob = await response.blob()

  const contentDisposition = response.headers.get('content-disposition') || ''
  const filename = parseDownloadFilename(contentDisposition)

  return { blob, filename }
}

export async function createDoctorPdfShareLink(shareUrl: string): Promise<DoctorPdfShareResponse> {
  const response = await doctorFetchRaw(shareUrl, {
    method: 'POST',
  })
  return response.json() as Promise<DoctorPdfShareResponse>
}

function parseDownloadFilename(contentDisposition: string): string {
  const utfMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utfMatch?.[1]) {
    return ensurePdfExtension(decodeURIComponent(utfMatch[1]))
  }

  const plainMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
  if (plainMatch?.[1]) {
    return ensurePdfExtension(plainMatch[1])
  }

  return 'report.pdf'
}

function ensurePdfExtension(filename: string): string {
  return filename.toLowerCase().endsWith('.pdf') ? filename : `${filename}.pdf`
}
