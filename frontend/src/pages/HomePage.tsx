/**
 * Главная страница - валидация токена
 */

import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Loader2, AlertCircle } from 'lucide-react'
import { validateToken, startSurvey } from '@/api'
import { Branding } from '@/components/layout/Branding'
import { useSurveyStore } from '@/store'

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [patientName, setPatientName] = useState<string | null>(null)
  const [consentChecked, setConsentChecked] = useState(false)
  const [isStarting, setIsStarting] = useState(false)

  const { setToken, setSession, setConfig } = useSurveyStore()

  useEffect(() => {
    if (!token) {
      setError('Ссылка недействительна. Пожалуйста, используйте ссылку из SMS или email.')
      setIsLoading(false)
      return
    }

    // Валидация токена
    validateToken(token)
      .then((response) => {
        if (response.valid) {
          setPatientName(response.patient_name || null)
          setToken(token)
          if (response.session_id) {
            setSession(response.session_id, response.patient_name || undefined, response.expires_at)
          }
        } else {
          setError('Ссылка недействительна или срок её действия истёк.')
        }
      })
      .catch((err) => {
        console.error('Token validation error:', err)
        setError(err.message || 'Ошибка проверки ссылки')
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [token, setToken, setSession])

  const handleStart = async () => {
    if (!token || !consentChecked) return

    setIsStarting(true)
    try {
      const response = await startSurvey(token, true)
      setSession(response.session_id, response.patient_name || undefined, response.expires_at)
      setConfig(response.survey_config)
      navigate('/survey')
    } catch (err) {
      console.error('Start survey error:', err)
      setError(err instanceof Error ? err.message : 'Ошибка при начале опроса')
    } finally {
      setIsStarting(false)
    }
  }

  // Загрузка
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center"
        >
          <Loader2 className="w-12 h-12 text-primary-600 animate-spin mx-auto" />
          <p className="mt-4 text-slate-600">Проверка ссылки...</p>
        </motion.div>
      </div>
    )
  }

  // Ошибка
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md"
        >
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h1 className="mt-4 text-xl font-semibold text-slate-900">
            Ссылка недействительна
          </h1>
          <p className="mt-2 text-slate-600">{error}</p>
          <p className="mt-4 text-sm text-slate-500">
            Если вы считаете, что это ошибка, свяжитесь с клиникой.
          </p>
        </motion.div>
      </div>
    )
  }

  // Экран приветствия и согласия
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-100">
        <div className="max-w-lg mx-auto px-4 h-14 flex items-center">
          <Branding />
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full"
        >
          {/* Приветствие */}
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-slate-900">
              {patientName ? `Здравствуйте, ${patientName}!` : 'Здравствуйте!'}
            </h1>
            <p className="mt-3 text-slate-600">
              Пожалуйста, ответьте на несколько вопросов. Это поможет врачу
              подготовиться к приёму и уделить больше времени осмотру, а не
              заполнению карт.
            </p>
          </div>

          {/* Согласие */}
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                className="mt-1 w-5 h-5 rounded border-slate-300 text-primary-600 
                           focus:ring-primary-500 focus:ring-offset-0"
              />
              <span className="text-sm text-slate-700">
                Я даю согласие на обработку персональных данных и передачу
                сведений о состоянии здоровья в медицинскую организацию (в
                соответствии с 152-ФЗ).
              </span>
            </label>
          </div>

          {/* Кнопка */}
          <motion.button
            whileTap={{ scale: 0.98 }}
            onClick={handleStart}
            disabled={!consentChecked || isStarting}
            className="btn-primary w-full mt-6 py-4 text-lg"
          >
            {isStarting ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                Загрузка...
              </span>
            ) : (
              'Начать'
            )}
          </motion.button>

          {/* Время */}
          <p className="mt-4 text-center text-sm text-slate-500">
            Опрос займёт около 2-3 минут
          </p>
        </motion.div>
      </main>
    </div>
  )
}

export default HomePage
