import { startTransition, useDeferredValue, useEffect, useMemo, useState } from 'react'

import {
  doctorLogin,
  fetchDoctorPdf,
  fetchDoctorPreviewHtml,
  getDoctorMe,
  getDoctorSessions,
} from '@/api/doctorApi'
import { useDoctorStore } from '@/store/doctorStore'
import type { DoctorClinicBucket, DoctorSessionItem } from '@/types'

import DoctorDashboard from './DoctorDashboard'
import DoctorLogin from './DoctorLogin'

const DOCTOR_PORTAL_TABS: Array<{ id: DoctorClinicBucket; label: string }> = [
  { id: 'novosibirsk', label: 'Новосибирск' },
  { id: 'kemerovo', label: 'Кемерово' },
  { id: 'yaroslavl', label: 'Ярославль' },
  { id: 'test', label: 'Тест' },
]

function getAvailableTabs(canViewTestTab: boolean) {
  return DOCTOR_PORTAL_TABS.filter((tab) => canViewTestTab || tab.id !== 'test')
}

export default function DoctorPortalPage() {
  const {
    token,
    doctor,
    filters,
    activeClinicBucket,
    hydrateAuth,
    setAuth,
    clearAuth,
    setDoctorNameFilter,
    setDateFrom,
    setDateTo,
    setActiveClinicBucket,
    resetFilters,
  } = useDoctorStore()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState<string | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [isBootstrapping, setIsBootstrapping] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingSessions, setIsLoadingSessions] = useState(false)
  const [isActionLoading, setIsActionLoading] = useState(false)
  const [sessions, setSessions] = useState<DoctorSessionItem[]>([])
  const deferredDoctorName = useDeferredValue(filters.doctorName)

  useEffect(() => {
    hydrateAuth()
  }, [hydrateAuth])

  useEffect(() => {
    let cancelled = false

    if (!token) {
      setIsBootstrapping(false)
      return () => {
        cancelled = true
      }
    }

    setIsBootstrapping(true)
    setAuthError(null)

    getDoctorMe()
      .then((currentDoctor) => {
        if (cancelled) return
        setAuth(token, currentDoctor)
      })
      .catch((error: Error) => {
        if (cancelled) return
        clearAuth()
        setAuthError(error.message)
      })
      .finally(() => {
        if (!cancelled) {
          setIsBootstrapping(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [token, clearAuth, setAuth])

  const availableTabs = useMemo(
    () => getAvailableTabs(Boolean(doctor?.can_view_test_tab)),
    [doctor?.can_view_test_tab]
  )

  useEffect(() => {
    if (!doctor) return

    const hasActiveTab = availableTabs.some((tab) => tab.id === activeClinicBucket)
    if (!hasActiveTab) {
      setActiveClinicBucket(availableTabs[0]?.id ?? 'novosibirsk')
    }
  }, [doctor, availableTabs, activeClinicBucket, setActiveClinicBucket])

  useEffect(() => {
    let cancelled = false

    if (!token || !doctor) {
      setSessions([])
      setListError(null)
      return () => {
        cancelled = true
      }
    }

    setIsLoadingSessions(true)
    setListError(null)

    getDoctorSessions({
      clinicBucket: activeClinicBucket,
      doctorName: deferredDoctorName.trim(),
      dateFrom: filters.dateFrom,
      dateTo: filters.dateTo,
    })
      .then((response) => {
        if (cancelled) return
        startTransition(() => {
          setSessions(response.items)
        })
      })
      .catch((error: Error) => {
        if (cancelled) return

        const lowerMessage = error.message.toLowerCase()
        if (lowerMessage.includes('авториза')) {
          clearAuth()
          setAuthError(error.message)
          return
        }

        if (lowerMessage.includes('доступ к тестовой вкладке')) {
          setActiveClinicBucket('novosibirsk')
          return
        }

        setListError(error.message)
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingSessions(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [
    token,
    doctor,
    activeClinicBucket,
    filters.dateFrom,
    filters.dateTo,
    deferredDoctorName,
    clearAuth,
    setActiveClinicBucket,
  ])

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setAuthError(null)

    try {
      const response = await doctorLogin(username.trim(), password)
      setAuth(response.access_token, response.doctor)
      setPassword('')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Не удалось выполнить вход.'
      setAuthError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handlePreview(session: DoctorSessionItem) {
    const previewWindow = window.open('', '_blank')
    if (!previewWindow) {
      setListError('Браузер заблокировал новое окно предпросмотра.')
      return
    }

    previewWindow.document.write('<p style="font-family:sans-serif;padding:24px">Загружаем отчет...</p>')
    setIsActionLoading(true)
    setListError(null)

    try {
      const html = await fetchDoctorPreviewHtml(session.preview_url)
      previewWindow.document.open()
      previewWindow.document.write(html)
      previewWindow.document.close()
    } catch (error) {
      previewWindow.close()
      const message = error instanceof Error ? error.message : 'Не удалось открыть отчет.'
      setListError(message)
    } finally {
      setIsActionLoading(false)
    }
  }

  async function handleDownload(session: DoctorSessionItem) {
    setIsActionLoading(true)
    setListError(null)

    try {
      const { blob, filename } = await fetchDoctorPdf(session.download_url)
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = filename
      link.style.display = 'none'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => {
        URL.revokeObjectURL(objectUrl)
      }, 1000)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Не удалось скачать PDF.'
      setListError(message)
    } finally {
      setIsActionLoading(false)
    }
  }

  function handleLogout() {
    clearAuth()
    setSessions([])
    setUsername('')
    setPassword('')
    setAuthError(null)
    setListError(null)
  }

  if (!token || !doctor || isBootstrapping) {
    return (
      <DoctorLogin
        username={username}
        password={password}
        isSubmitting={isSubmitting || isBootstrapping}
        error={authError}
        onUsernameChange={setUsername}
        onPasswordChange={setPassword}
        onSubmit={handleLogin}
      />
    )
  }

  return (
    <DoctorDashboard
      doctor={doctor}
      sessions={sessions}
      total={sessions.length}
      filters={filters}
      tabs={availableTabs}
      activeClinicBucket={activeClinicBucket}
      isLoading={isLoadingSessions}
      error={listError}
      isActionLoading={isActionLoading}
      onClinicBucketChange={setActiveClinicBucket}
      onDoctorNameChange={setDoctorNameFilter}
      onDateFromChange={setDateFrom}
      onDateToChange={setDateTo}
      onResetFilters={resetFilters}
      onLogout={handleLogout}
      onPreview={handlePreview}
      onDownload={handleDownload}
    />
  )
}
