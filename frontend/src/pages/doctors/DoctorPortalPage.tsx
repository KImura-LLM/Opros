import { startTransition, useDeferredValue, useEffect, useState } from 'react'

import {
  doctorLogin,
  fetchDoctorPdf,
  fetchDoctorPreviewHtml,
  getDoctorMe,
  getDoctorSessions,
} from '@/api/doctorApi'
import type { DoctorSessionItem } from '@/types'
import { useDoctorStore } from '@/store/doctorStore'

import DoctorDashboard from './DoctorDashboard'
import DoctorLogin from './DoctorLogin'

export default function DoctorPortalPage() {
  const {
    token,
    doctor,
    filters,
    hydrateAuth,
    setAuth,
    clearAuth,
    setDoctorNameFilter,
    setDateFrom,
    setDateTo,
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

  useEffect(() => {
    let cancelled = false

    if (!token) {
      setSessions([])
      setListError(null)
      return () => {
        cancelled = true
      }
    }

    setIsLoadingSessions(true)
    setListError(null)

    getDoctorSessions({
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
        if (error.message.toLowerCase().includes('авториза')) {
          clearAuth()
          setAuthError(error.message)
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
  }, [token, filters.dateFrom, filters.dateTo, deferredDoctorName, clearAuth])

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
      isLoading={isLoadingSessions}
      error={listError}
      isActionLoading={isActionLoading}
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
