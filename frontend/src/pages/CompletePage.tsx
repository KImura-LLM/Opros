/**
 * Страница успешного завершения опроса
 * 
 * Оптимизирована для мгновенного отображения (< 1 сек визуально).
 * Все тяжёлые процессы (PDF, Битрикс24) выполняются фоново на сервере,
 * пока пользователь уже видит финальный экран.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircle } from 'lucide-react'
import { useSurveyStore } from '@/store'
import { Branding } from '@/components/layout/Branding'

const CompletePage: React.FC = () => {
  const { patientName, reset } = useSurveyStore()

  // Сброс состояния при размонтировании
  React.useEffect(() => {
    return () => {
      reset()
    }
  }, [reset])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-100">
        <div className="max-w-lg mx-auto px-4 h-14 flex items-center">
          <Branding />
        </div>
      </header>

      {/* Content — мгновенное появление */}
      <main className="flex-1 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="text-center max-w-md"
        >
          {/* Анимированная галочка — мгновенный spring */}
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{
              delay: 0.05,
              type: 'spring',
              stiffness: 300,
              damping: 20,
            }}
            className="mx-auto"
          >
            <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle className="w-12 h-12 text-green-500" />
            </div>
          </motion.div>

          {/* Текст — появляется почти сразу */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.2, ease: 'easeOut' }}
          >
            <h1 className="mt-6 text-2xl font-bold text-slate-900">
              Спасибо{patientName ? `, ${patientName}` : ''}!
            </h1>
            <p className="mt-3 text-slate-600">
              Анкета заполнена. Данные переданы врачу, он изучит их до начала
              приёма.
            </p>
          </motion.div>

          {/* Подсказка — плавное проявление */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.3 }}
            className="mt-8 text-sm text-slate-400"
          >
            Вы можете закрыть эту страницу
          </motion.p>
        </motion.div>
      </main>
    </div>
  )
}

export default CompletePage
