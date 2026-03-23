import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import type { DoctorFilters, DoctorMeResponse } from '@/types'

const FILTERS_STORAGE_KEY = 'opros_doctor_filters'
const AUTH_STORAGE_KEY = 'opros_doctor_auth'

const defaultFilters: DoctorFilters = {
  doctorName: '',
  dateFrom: '',
  dateTo: '',
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
      typeof parsed.doctor.username === 'string'
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
  hydrateAuth: () => void
  setAuth: (token: string, doctor: DoctorMeResponse) => void
  clearAuth: () => void
  setDoctorNameFilter: (value: string) => void
  setDateFrom: (value: string) => void
  setDateTo: (value: string) => void
  resetFilters: () => void
}

export const useDoctorStore = create<DoctorStoreState>()(
  persist(
    (set) => ({
      token: null,
      doctor: null,
      filters: defaultFilters,

      hydrateAuth: () => {
        const auth = readDoctorAuth()
        if (!auth) return
        set({ token: auth.token, doctor: auth.doctor })
      },

      setAuth: (token, doctor) => {
        saveDoctorAuth(token, doctor)
        set({ token, doctor })
      },

      clearAuth: () => {
        clearDoctorAuthStorage()
        set({ token: null, doctor: null })
      },

      setDoctorNameFilter: (value) =>
        set((state) => ({
          filters: {
            ...state.filters,
            doctorName: value,
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
      }),
    }
  )
)
