import {
  ArrowDownNarrowWide,
  ArrowUpNarrowWide,
  Building2,
  CalendarRange,
  Download,
  Eye,
  Filter,
  LogOut,
  RefreshCw,
  Share2,
} from 'lucide-react'

import type {
  DoctorClinicBucket,
  DoctorFilters,
  DoctorMeResponse,
  DoctorSessionItem,
  DoctorSessionSortField,
  DoctorSessionSortOrder,
} from '@/types'

interface DoctorClinicTab {
  id: DoctorClinicBucket
  label: string
}

const dateTimeFormatter = new Intl.DateTimeFormat('ru-RU', {
  dateStyle: 'short',
  timeStyle: 'short',
})

interface DoctorDashboardProps {
  doctor: DoctorMeResponse
  sessions: DoctorSessionItem[]
  total: number
  filters: DoctorFilters
  tabs: DoctorClinicTab[]
  activeClinicBucket: DoctorClinicBucket
  sortField: DoctorSessionSortField
  sortOrder: DoctorSessionSortOrder
  isLoading: boolean
  error: string | null
  isActionLoading: boolean
  shareStatus: string | null
  onClinicBucketChange: (value: DoctorClinicBucket) => void
  onDoctorNameChange: (value: string) => void
  onDateFromChange: (value: string) => void
  onDateToChange: (value: string) => void
  onResetFilters: () => void
  onLogout: () => void
  onSortChange: (field: DoctorSessionSortField) => void
  onPreview: (session: DoctorSessionItem) => void
  onDownload: (session: DoctorSessionItem) => void
  onShare: (session: DoctorSessionItem) => void
}

function formatDateTime(value?: string): string {
  if (!value) return 'Не указано'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Не указано'
  return dateTimeFormatter.format(date)
}

function formatDuration(value?: number): string {
  if (value === undefined || value === null) return 'Не указано'
  if (value <= 0) return '0 мин'
  return `${value} мин`
}

function formatAppointmentDateTime(value?: string): string {
  if (!value) return 'Не указано'

  const normalized = value.trim().replace(/\s+/, ' ')
  const match = normalized.match(/^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})$/)
  if (match) {
    return `${match[1]}, ${match[2]}`
  }

  const parsedDate = new Date(normalized)
  if (!Number.isNaN(parsedDate.getTime())) {
    return dateTimeFormatter.format(parsedDate)
  }

  return value
}

interface SortableHeaderProps {
  field: DoctorSessionSortField
  label: string
  activeField: DoctorSessionSortField
  order: DoctorSessionSortOrder
  onSortChange: (field: DoctorSessionSortField) => void
}

function SortableHeader({
  field,
  label,
  activeField,
  order,
  onSortChange,
}: SortableHeaderProps) {
  const isActive = field === activeField

  return (
    <button
      className={`inline-flex items-center gap-2 text-left text-xs font-semibold uppercase tracking-[0.2em] transition ${
        isActive ? 'text-slate-900' : 'text-slate-500 hover:text-slate-700'
      }`}
      type="button"
      onClick={() => onSortChange(field)}
      title={`Сортировать по колонке "${label}"`}
    >
      {label}
      {isActive ? (
        order === 'asc' ? (
          <ArrowUpNarrowWide className="h-4 w-4" />
        ) : (
          <ArrowDownNarrowWide className="h-4 w-4" />
        )
      ) : (
        <ArrowDownNarrowWide className="h-4 w-4 opacity-25" />
      )}
    </button>
  )
}

export default function DoctorDashboard({
  doctor,
  sessions,
  total,
  filters,
  tabs,
  activeClinicBucket,
  sortField,
  sortOrder,
  isLoading,
  error,
  isActionLoading,
  shareStatus,
  onClinicBucketChange,
  onDoctorNameChange,
  onDateFromChange,
  onDateToChange,
  onResetFilters,
  onLogout,
  onSortChange,
  onPreview,
  onDownload,
  onShare,
}: DoctorDashboardProps) {
  const activeTabLabel = tabs.find((tab) => tab.id === activeClinicBucket)?.label ?? 'Сессии'

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#f6fbfa_0%,_#eef6f4_48%,_#ffffff_100%)] text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 overflow-hidden rounded-[32px] border border-white/80 bg-[linear-gradient(135deg,_rgba(15,118,110,0.96)_0%,_rgba(17,94,89,0.96)_44%,_rgba(15,23,42,0.96)_100%)] p-6 text-white shadow-[0_24px_70px_-36px_rgba(15,23,42,0.75)]">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.24em] text-teal-100">
                <CalendarRange className="h-4 w-4" />
                Портал врача
              </div>
              <div>
                <h1 className="font-serif text-3xl leading-tight sm:text-4xl">
                  Завершенные сессии пациентов
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-200 sm:text-base">
                  Данные разложены по клиникам. Можно быстро переключаться между вкладками,
                  сузить список по врачу и периоду, открыть отчет или скачать PDF.
                </p>
              </div>
            </div>

            <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
              <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur">
                <div className="text-xs uppercase tracking-[0.24em] text-teal-100">Вошли как</div>
                <div className="mt-1 text-lg font-semibold text-white">{doctor.username}</div>
              </div>
              <button
                className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/15"
                type="button"
                onClick={onLogout}
              >
                <LogOut className="h-4 w-4" />
                Выйти
              </button>
            </div>
          </div>
        </header>

        <section className="mb-6 rounded-[28px] border border-slate-200 bg-white/90 p-5 shadow-[0_24px_60px_-42px_rgba(15,23,42,0.65)] backdrop-blur">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            <Building2 className="h-4 w-4" />
            Вкладки клиник
          </div>

          <div className="flex flex-wrap gap-3">
            {tabs.map((tab) => {
              const isActive = tab.id === activeClinicBucket
              return (
                <button
                  key={tab.id}
                  className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                    isActive
                      ? 'bg-slate-900 text-white shadow-[0_18px_30px_-20px_rgba(15,23,42,0.85)]'
                      : 'border border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-white'
                  }`}
                  type="button"
                  onClick={() => onClinicBucketChange(tab.id)}
                >
                  {tab.label}
                </button>
              )
            })}
          </div>
        </section>

        <section className="mb-6 rounded-[28px] border border-slate-200 bg-white/90 p-5 shadow-[0_24px_60px_-42px_rgba(15,23,42,0.65)] backdrop-blur">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            <Filter className="h-4 w-4" />
            Фильтры
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_repeat(2,minmax(0,0.6fr))_auto]">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Поиск по врачу</span>
              <input
                className="input-field"
                type="text"
                value={filters.doctorName}
                onChange={(event) => onDoctorNameChange(event.target.value)}
                placeholder="Например, Иванова"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Дата от</span>
              <input
                className="input-field"
                type="date"
                value={filters.dateFrom}
                onChange={(event) => onDateFromChange(event.target.value)}
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Дата до</span>
              <input
                className="input-field"
                type="date"
                value={filters.dateTo}
                onChange={(event) => onDateToChange(event.target.value)}
              />
            </label>

            <div className="flex items-end">
              <button
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                type="button"
                onClick={onResetFilters}
              >
                <RefreshCw className="h-4 w-4" />
                Сбросить
              </button>
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_24px_60px_-42px_rgba(15,23,42,0.65)]">
          <div className="flex flex-col gap-2 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-semibold text-slate-900">
                {activeTabLabel}: найдено сессий {total}
              </div>
              <div className="text-sm text-slate-500">
                {isLoading
                  ? 'Обновляем список...'
                  : 'Показываются только завершенные анкеты. Сортировку можно менять нажатием на заголовок любой колонки.'}
              </div>
            </div>
            {isActionLoading ? (
              <div className="text-sm text-teal-700">Готовим файл или окно предпросмотра...</div>
            ) : null}
            {shareStatus ? (
              <div className="text-sm text-teal-700">{shareStatus}</div>
            ) : null}
          </div>

          {error ? (
            <div className="border-b border-rose-100 bg-rose-50 px-5 py-4 text-sm text-rose-700">
              {error}
            </div>
          ) : null}

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50/80">
                <tr className="text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  <th className="px-5 py-4">
                    <SortableHeader
                      field="patient_name"
                      label="Пациент"
                      activeField={sortField}
                      order={sortOrder}
                      onSortChange={onSortChange}
                    />
                  </th>
                  <th className="px-5 py-4">
                    <SortableHeader
                      field="doctor_name"
                      label="Врач"
                      activeField={sortField}
                      order={sortOrder}
                      onSortChange={onSortChange}
                    />
                  </th>
                  <th className="px-5 py-4">
                    <SortableHeader
                      field="appointment_at"
                      label="Дата и время приема"
                      activeField={sortField}
                      order={sortOrder}
                      onSortChange={onSortChange}
                    />
                  </th>
                  <th className="px-5 py-4">
                    <SortableHeader
                      field="start_time"
                      label="Начало"
                      activeField={sortField}
                      order={sortOrder}
                      onSortChange={onSortChange}
                    />
                  </th>
                  <th className="px-5 py-4">
                    <SortableHeader
                      field="end_time"
                      label="Окончание"
                      activeField={sortField}
                      order={sortOrder}
                      onSortChange={onSortChange}
                    />
                  </th>
                  <th className="px-5 py-4">
                    <SortableHeader
                      field="duration_minutes"
                      label="Длительность"
                      activeField={sortField}
                      order={sortOrder}
                      onSortChange={onSortChange}
                    />
                  </th>
                  <th className="px-5 py-4">Отчет</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.length === 0 && !isLoading ? (
                  <tr>
                    <td className="px-5 py-10 text-center text-sm text-slate-500" colSpan={7}>
                      По текущим фильтрам завершенные сессии не найдены.
                    </td>
                  </tr>
                ) : null}

                {sessions.map((session) => (
                  <tr key={session.session_id} className="transition hover:bg-slate-50/80">
                    <td className="px-5 py-4 text-sm font-medium text-slate-900">
                      {session.patient_name || 'Не указано'}
                    </td>
                    <td className="px-5 py-4 text-sm text-slate-700">
                      {session.doctor_name || 'Не указано'}
                    </td>
                    <td className="px-5 py-4 text-sm text-slate-700">
                      {formatAppointmentDateTime(session.appointment_at)}
                    </td>
                    <td className="px-5 py-4 text-sm text-slate-700">
                      {formatDateTime(session.start_time)}
                    </td>
                    <td className="px-5 py-4 text-sm text-slate-700">
                      {formatDateTime(session.end_time)}
                    </td>
                    <td className="px-5 py-4 text-sm text-slate-700">
                      {formatDuration(session.duration_minutes)}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap gap-2">
                        <button
                          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                          type="button"
                          onClick={() => onPreview(session)}
                        >
                          <Eye className="h-4 w-4" />
                          Просмотр
                        </button>
                        <button
                          className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-teal-700"
                          type="button"
                          onClick={() => onDownload(session)}
                        >
                          <Download className="h-4 w-4" />
                          PDF
                        </button>
                        <button
                          className="inline-flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-medium text-teal-800 transition hover:border-teal-300 hover:bg-teal-100"
                          type="button"
                          onClick={() => onShare(session)}
                        >
                          <Share2 className="h-4 w-4" />
                          Поделиться
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}
