import { startTransition, useDeferredValue, useEffect, useMemo, useState } from 'react'

import {
  createDoctorPdfShareLink,
  doctorLogin,
  fetchDoctorPdf,
  fetchDoctorPreviewHtml,
  getDoctorMe,
  getDoctorSessions,
} from '@/api/doctorApi'
import { useDoctorStore } from '@/store/doctorStore'
import type {
  DoctorClinicBucket,
  DoctorMeResponse,
  DoctorSessionItem,
  DoctorSessionSortField,
  DoctorSessionSortOrder,
} from '@/types'

import DoctorDashboard from './DoctorDashboard'
import DoctorLogin from './DoctorLogin'

const DOCTOR_PORTAL_TABS: Array<{ id: DoctorClinicBucket; label: string }> = [
  { id: 'novosibirsk', label: 'Новосибирск' },
  { id: 'kemerovo', label: 'Кемерово' },
  { id: 'yaroslavl', label: 'Ярославль' },
  { id: 'test', label: 'Тест' },
]

const NEAREST_SESSIONS_LIMIT = 3

const CLINIC_BUCKET_UTC_OFFSETS: Record<DoctorClinicBucket, number> = {
  novosibirsk: 7,
  kemerovo: 7,
  yaroslavl: 3,
  test: 7,
}

const textCollator = new Intl.Collator('ru-RU', {
  numeric: true,
  sensitivity: 'base',
})

function getAvailableTabs(doctor: DoctorMeResponse | null) {
  if (doctor?.allowed_clinic_bucket) {
    return DOCTOR_PORTAL_TABS.filter((tab) => tab.id === doctor.allowed_clinic_bucket)
  }

  return DOCTOR_PORTAL_TABS.filter((tab) => doctor?.can_view_test_tab || tab.id !== 'test')
}

function parseAppointmentTimestamp(value?: string): number | null {
  if (!value) return null

  const [datePart, timePart = '00:00'] = value.trim().split(' ')
  const [day, month, year] = datePart.split('.').map(Number)
  const [hours, minutes] = timePart.split(':').map(Number)

  if (
    !Number.isInteger(day) ||
    !Number.isInteger(month) ||
    !Number.isInteger(year) ||
    !Number.isInteger(hours) ||
    !Number.isInteger(minutes)
  ) {
    return null
  }

  return new Date(year, month - 1, day, hours, minutes).getTime()
}

function parseAppointmentTimestampInClinicTimezone(
  value: string | undefined,
  clinicBucket: DoctorClinicBucket
): number | null {
  if (!value) return null

  const normalized = value.trim().replace(/\s+/, ' ')
  const [datePart, timePart = '00:00'] = normalized.split(' ')
  const [day, month, year] = datePart.split('.').map(Number)
  const [hours, minutes] = timePart.split(':').map(Number)

  if (
    !Number.isInteger(day) ||
    !Number.isInteger(month) ||
    !Number.isInteger(year) ||
    !Number.isInteger(hours) ||
    !Number.isInteger(minutes)
  ) {
    return null
  }

  const utcOffset = CLINIC_BUCKET_UTC_OFFSETS[clinicBucket]
  return Date.UTC(year, month - 1, day, hours - utcOffset, minutes)
}

function parseIsoTimestamp(value?: string): number | null {
  if (!value) return null
  const timestamp = new Date(value).getTime()
  return Number.isNaN(timestamp) ? null : timestamp
}

function compareNullableNumbers(
  left: number | null,
  right: number | null,
  order: DoctorSessionSortOrder
): number {
  if (left === null && right === null) return 0
  if (left === null) return 1
  if (right === null) return -1
  return order === 'asc' ? left - right : right - left
}

function compareNullableStrings(
  left: string | undefined,
  right: string | undefined,
  order: DoctorSessionSortOrder
): number {
  const normalizedLeft = left?.trim() || null
  const normalizedRight = right?.trim() || null

  if (normalizedLeft === null && normalizedRight === null) return 0
  if (normalizedLeft === null) return 1
  if (normalizedRight === null) return -1

  const result = textCollator.compare(normalizedLeft, normalizedRight)
  return order === 'asc' ? result : -result
}

function compareSessionsByField(
  left: DoctorSessionItem,
  right: DoctorSessionItem,
  field: DoctorSessionSortField,
  order: DoctorSessionSortOrder
): number {
  switch (field) {
    case 'patient_name':
      return compareNullableStrings(left.patient_name, right.patient_name, order)
    case 'doctor_name':
      return compareNullableStrings(left.doctor_name, right.doctor_name, order)
    case 'appointment_at':
      return compareNullableNumbers(
        parseAppointmentTimestamp(left.appointment_at),
        parseAppointmentTimestamp(right.appointment_at),
        order
      )
    case 'start_time':
      return compareNullableNumbers(parseIsoTimestamp(left.start_time), parseIsoTimestamp(right.start_time), order)
    case 'end_time':
      return compareNullableNumbers(parseIsoTimestamp(left.end_time), parseIsoTimestamp(right.end_time), order)
    case 'duration_minutes':
      return compareNullableNumbers(left.duration_minutes ?? null, right.duration_minutes ?? null, order)
    default:
      return 0
  }
}

function normalizeDoctorName(value?: string): string {
  return value?.trim().toLocaleLowerCase('ru-RU') || 'doctor-name-not-set'
}

function getNearestSessionRanks(
  sessions: DoctorSessionItem[],
  clinicBucket: DoctorClinicBucket,
  nowTimestamp: number
): Map<string, number> {
  const groupedSessions = new Map<string, Array<{ session: DoctorSessionItem; appointmentTimestamp: number }>>()

  for (const session of sessions) {
    const appointmentTimestamp = parseAppointmentTimestampInClinicTimezone(session.appointment_at, clinicBucket)
    if (appointmentTimestamp === null || appointmentTimestamp <= nowTimestamp) {
      continue
    }

    const doctorName = normalizeDoctorName(session.doctor_name)
    const group = groupedSessions.get(doctorName) ?? []
    group.push({ session, appointmentTimestamp })
    groupedSessions.set(doctorName, group)
  }

  const ranks = new Map<string, number>()

  groupedSessions.forEach((group) => {
    group
      .sort((left, right) => left.appointmentTimestamp - right.appointmentTimestamp)
      .slice(0, NEAREST_SESSIONS_LIMIT)
      .forEach((item, index) => {
        ranks.set(item.session.session_id, index + 1)
      })
  })

  return ranks
}

function sortNearestSessions(
  sessions: DoctorSessionItem[],
  ranks: Map<string, number>,
  clinicBucket: DoctorClinicBucket
): DoctorSessionItem[] {
  return [...sessions]
    .filter((session) => ranks.has(session.session_id))
    .sort((left, right) => {
      const rankCompare = (ranks.get(left.session_id) ?? 0) - (ranks.get(right.session_id) ?? 0)
      if (rankCompare !== 0) return rankCompare

      const leftTimestamp = parseAppointmentTimestampInClinicTimezone(left.appointment_at, clinicBucket)
      const rightTimestamp = parseAppointmentTimestampInClinicTimezone(right.appointment_at, clinicBucket)
      const dateCompare = compareNullableNumbers(leftTimestamp, rightTimestamp, 'asc')
      if (dateCompare !== 0) return dateCompare

      return compareNullableStrings(left.doctor_name, right.doctor_name, 'asc')
    })
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
    setPatientNameFilter,
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
  const [shareStatus, setShareStatus] = useState<string | null>(null)
  const [sessions, setSessions] = useState<DoctorSessionItem[]>([])
  const [sortField, setSortField] = useState<DoctorSessionSortField>('appointment_at')
  const [sortOrder, setSortOrder] = useState<DoctorSessionSortOrder>('desc')
  const [showNearestOnly, setShowNearestOnly] = useState(false)
  const [currentTimestamp, setCurrentTimestamp] = useState(() => Date.now())
  const deferredDoctorName = useDeferredValue(filters.doctorName)
  const deferredPatientName = useDeferredValue(filters.patientName ?? '')
  const shouldHideDoctorNameFilter = Boolean(doctor?.has_strict_doctor_name_filter)

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

  const availableTabs = useMemo(() => getAvailableTabs(doctor), [doctor])

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
      doctorName: shouldHideDoctorNameFilter ? '' : deferredDoctorName.trim(),
      patientName: deferredPatientName.trim(),
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

        if (
          lowerMessage.includes('доступ к тестовой вкладке') ||
          lowerMessage.includes('доступ к выбранной вкладке')
        ) {
          setActiveClinicBucket(doctor.allowed_clinic_bucket ?? 'novosibirsk')
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
    deferredPatientName,
    shouldHideDoctorNameFilter,
    clearAuth,
    setActiveClinicBucket,
  ])

  const sortedSessions = useMemo(() => {
    return [...sessions].sort((left, right) => {
      return compareSessionsByField(left, right, sortField, sortOrder)
    })
  }, [sessions, sortField, sortOrder])

  useEffect(() => {
    const timerId = window.setInterval(() => {
      setCurrentTimestamp(Date.now())
    }, 60_000)

    return () => {
      window.clearInterval(timerId)
    }
  }, [])

  const nearestSessionRanks = useMemo(() => {
    return getNearestSessionRanks(sessions, activeClinicBucket, currentTimestamp)
  }, [sessions, activeClinicBucket, currentTimestamp])

  const visibleSessions = useMemo(() => {
    if (!showNearestOnly) {
      return sortedSessions
    }

    return sortNearestSessions(sessions, nearestSessionRanks, activeClinicBucket)
  }, [sessions, sortedSessions, showNearestOnly, nearestSessionRanks, activeClinicBucket])

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

  async function copyTextToClipboard(text: string): Promise<void> {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return
    }

    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()

    try {
      if (!document.execCommand('copy')) {
        throw new Error('copy command failed')
      }
    } finally {
      textarea.remove()
    }
  }

  function normalizeShareUrl(value: string): string {
    if (/^https?:\/\//i.test(value)) {
      return value
    }

    const normalizedPath = value.startsWith('/') ? value : `/${value}`
    return `${window.location.origin}${normalizedPath}`
  }

  async function handleShare(session: DoctorSessionItem) {
    setIsActionLoading(true)
    setListError(null)
    setShareStatus(null)

    try {
      const response = await createDoctorPdfShareLink(session.share_url)
      const shareUrl = normalizeShareUrl(response.share_url)
      await copyTextToClipboard(shareUrl)
      setShareStatus(`Ссылка на PDF скопирована. Она действует ${response.expires_in_hours} ч.`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Не удалось скопировать ссылку на PDF.'
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
    setShareStatus(null)
    setShowNearestOnly(false)
  }

  function handleSortChange(field: DoctorSessionSortField) {
    if (field === sortField) {
      setSortOrder((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }

    setSortField(field)
    setSortOrder(field === 'appointment_at' || field === 'start_time' || field === 'end_time' ? 'desc' : 'asc')
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
      sessions={visibleSessions}
      total={visibleSessions.length}
      filters={filters}
      showDoctorNameFilter={!shouldHideDoctorNameFilter}
      tabs={availableTabs}
      activeClinicBucket={activeClinicBucket}
      sortField={sortField}
      sortOrder={sortOrder}
      isLoading={isLoadingSessions}
      error={listError}
      isActionLoading={isActionLoading}
      shareStatus={shareStatus}
      nearestSessionRanks={nearestSessionRanks}
      showNearestOnly={showNearestOnly}
      hasNearestSessions={nearestSessionRanks.size > 0}
      onClinicBucketChange={setActiveClinicBucket}
      onDoctorNameChange={setDoctorNameFilter}
      onPatientNameChange={setPatientNameFilter}
      onDateFromChange={setDateFrom}
      onDateToChange={setDateTo}
      onResetFilters={resetFilters}
      onToggleNearestSessions={() => setShowNearestOnly((current) => !current)}
      onLogout={handleLogout}
      onSortChange={handleSortChange}
      onPreview={handlePreview}
      onDownload={handleDownload}
      onShare={handleShare}
    />
  )
}
