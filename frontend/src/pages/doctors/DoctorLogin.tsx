import { LockKeyhole, Stethoscope, UserRound } from 'lucide-react'

interface DoctorLoginProps {
  username: string
  password: string
  isSubmitting: boolean
  error: string | null
  onUsernameChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
}

export default function DoctorLogin({
  username,
  password,
  isSubmitting,
  error,
  onUsernameChange,
  onPasswordChange,
  onSubmit,
}: DoctorLoginProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(20,184,166,0.18),_transparent_28%),linear-gradient(135deg,_#f8fafc_0%,_#e2f5f1_42%,_#fdfaf5_100%)]">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(15,118,110,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(15,118,110,0.05)_1px,transparent_1px)] bg-[size:32px_32px]" />

      <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6 py-12 lg:flex-row lg:items-center lg:gap-16">
        <section className="max-w-xl space-y-6 text-slate-900">
          <div className="inline-flex items-center gap-3 rounded-full border border-teal-200 bg-white/80 px-4 py-2 text-sm font-medium text-teal-800 shadow-sm backdrop-blur">
            <Stethoscope className="h-4 w-4" />
            Закрытый портал результатов для врачей
          </div>

          <div className="space-y-4">
            <h1 className="font-serif text-4xl leading-tight text-slate-950 md:text-5xl">
              Быстрый доступ к завершенным анкетам пациентов
            </h1>
            <p className="max-w-lg text-base leading-7 text-slate-700 md:text-lg">
              Войдите под учетной записью врача, чтобы открыть список завершенных сессий,
              отфильтровать их по периоду и сразу перейти к просмотру PDF-отчета.
            </p>
          </div>

          <div className="grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
          </div>
        </section>

        <section className="mt-10 w-full max-w-md lg:mt-0">
          <div className="rounded-[28px] border border-white/80 bg-white/90 p-7 shadow-[0_24px_80px_-36px_rgba(15,23,42,0.55)] backdrop-blur">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-900 text-white shadow-lg shadow-teal-900/20">
                <LockKeyhole className="h-5 w-5" />
              </div>
              <div>
                <div className="text-sm font-medium uppercase tracking-[0.18em] text-teal-700">
                  Авторизация
                </div>
                <div className="text-lg font-semibold text-slate-950">Вход для врача</div>
              </div>
            </div>

            <form className="space-y-4" onSubmit={onSubmit}>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Логин</span>
                <div className="relative">
                  <UserRound className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    className="input-field pl-11"
                    type="text"
                    autoComplete="username"
                    value={username}
                    onChange={(event) => onUsernameChange(event.target.value)}
                    placeholder="Введите логин"
                    disabled={isSubmitting}
                  />
                </div>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Пароль</span>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    className="input-field pl-11"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => onPasswordChange(event.target.value)}
                    placeholder="Введите пароль"
                    disabled={isSubmitting}
                  />
                </div>
              </label>

              {error ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {error}
                </div>
              ) : null}

              <button className="btn-primary w-full justify-center" type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Проверяем доступ...' : 'Войти в портал'}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  )
}
