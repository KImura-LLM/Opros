import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import type {
  DoctorClinicBucket,
  DoctorFilters,
  DoctorMeResponse,
} from '@/types'

const FILTERS_STORAGE_KEY = 'opros_doctor_filters'
const AUTH_STORAGE_KEY = 'opros_doctor_auth'
const DEFAULT_CLINIC_BUCKET: DoctorClinicBucket = 'novosibirsk'

const defaultFilters: DoctorFilters = {
  doctorName: '',
  patientName: '',
  dateFrom: '',
  dateTo: '',
}

function normalizeFiltersForDoctor(
  filters: DoctorFilters,
  doctor: DoctorMeResponse | null
): DoctorFilters {
  if (!doctor?.has_strict_doctor_name_filter) {
    return filters
  }

  if (!filters.doctorName) {
    return filters
  }

  return {
    ...filters,
    doctorName: '',
  }
}

function normalizeClinicBucketForDoctor(
  clinicBucket: DoctorClinicBucket,
  doctor: DoctorMeResponse | null
): DoctorClinicBucket {
  if (doctor?.allowed_clinic_bucket) {
    return doctor.allowed_clinic_bucket
  }

  if (clinicBucket === 'test' && !doctor?.can_view_test_tab) {
    return DEFAULT_CLINIC_BUCKET
  }

  return clinicBucket
}

function saveDoctorAuth(token: string, doctor: DoctorMeResponse): void {
  try {
    sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token, doctor }))
  } catch {
    // sessionStorage может быть недоступен в некоторых окружениях
  }
}

function readDoctorAuth(): { token: string; doctor: DoctorMeResponse } | null {
  try {
    const raw = sessionStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null

    const parsed = JSON.parse(raw)
    if (
      parsed &&
      typeof parsed.token === 'string' &&
      parsed.doctor &&
      typeof parsed.doctor.id === 'number' &&
      typeof parsed.doctor.username === 'string' &&
      typeof parsed.doctor.can_view_test_tab === 'boolean' &&
      typeof parsed.doctor.has_strict_doctor_name_filter === 'boolean' &&
      (parsed.doctor.allowed_clinic_bucket === undefined ||
        parsed.doctor.allowed_clinic_bucket === null ||
        typeof parsed.doctor.allowed_clinic_bucket === 'string')
    ) {
      return parsed as { token: string; doctor: DoctorMeResponse }
    }
  } catch {
    clearDoctorAuthStorage()
  }

  return null
}

function clearDoctorAuthStorage(): void {
  try {
    sessionStorage.removeItem(AUTH_STORAGE_KEY)
  } catch {
    // Игнорируем сбой очистки в недоступном storage
  }
}

interface DoctorStoreState {
  token: string | null
  doctor: DoctorMeResponse | null
  filters: DoctorFilters
  activeClinicBucket: DoctorClinicBucket
  hydrateAuth: () => void
  setAuth: (token: string, doctor: DoctorMeResponse) => void
  clearAuth: () => void
  setDoctorNameFilter: (value: string) => void
  setPatientNameFilter: (value: string) => void
  setDateFrom: (value: string) => void
  setDateTo: (value: string) => void
  setActiveClinicBucket: (value: DoctorClinicBucket) => void
  resetFilters: () => void
}

export const useDoctorStore = create<DoctorStoreState>()(
  persist(
    (set, get) => ({
      token: null,
      doctor: null,
      filters: defaultFilters,
      activeClinicBucket: DEFAULT_CLINIC_BUCKET,

      hydrateAuth: () => {
        const auth = readDoctorAuth()
        if (!auth) return

        set({
          token: auth.token,
          doctor: auth.doctor,
          filters: normalizeFiltersForDoctor(get().filters, auth.doctor),
          activeClinicBucket: normalizeClinicBucketForDoctor(
            get().activeClinicBucket,
            auth.doctor
          ),
        })
      },

      setAuth: (token, doctor) => {
        saveDoctorAuth(token, doctor)
        set((state) => ({
          token,
          doctor,
          filters: normalizeFiltersForDoctor(state.filters, doctor),
          activeClinicBucket: normalizeClinicBucketForDoctor(
            state.activeClinicBucket,
            doctor
          ),
        }))
      },

      clearAuth: () => {
        clearDoctorAuthStorage()
        set({ token: null, doctor: null, activeClinicBucket: DEFAULT_CLINIC_BUCKET })
      },

      setDoctorNameFilter: (value) =>
        set((state) => ({
          filters: {
            ...state.filters,
            doctorName: value,
          },
        })),

      setPatientNameFilter: (value) =>
        set((state) => ({
          filters: {
            ...state.filters,
            patientName: value,
          },
        })),

      setDateFrom: (value) =>
        set((state) => ({
          filters: {
            ...state.filters,
            dateFrom: value,
          },
        })),

      setDateTo: (value) =>
        set((state) => ({
          filters: {
            ...state.filters,
            dateTo: value,
          },
        })),

      setActiveClinicBucket: (value) =>
        set((state) => ({
          activeClinicBucket: normalizeClinicBucketForDoctor(value, state.doctor),
        })),

      resetFilters: () =>
        set({
          filters: defaultFilters,
        }),
    }),
    {
      name: FILTERS_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        filters: state.filters,
        activeClinicBucket: state.activeClinicBucket,
      }),
    }
  )
)
