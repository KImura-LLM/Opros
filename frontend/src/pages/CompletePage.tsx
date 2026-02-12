/**
 * Страница успешного завершения опроса
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

      {/* Content */}
      <main className="flex-1 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="text-center max-w-md"
        >
          {/* Анимированная галочка */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{
              delay: 0.2,
              type: 'spring',
              stiffness: 200,
              damping: 15,
            }}
            className="mx-auto"
          >
            <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto">
              <motion.div
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ delay: 0.4, duration: 0.5 }}
              >
                <CheckCircle className="w-12 h-12 text-green-500" />
              </motion.div>
            </div>
          </motion.div>

          {/* Текст */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <h1 className="mt-6 text-2xl font-bold text-slate-900">
              Спасибо{patientName ? `, ${patientName}` : ''}!
            </h1>
            <p className="mt-3 text-slate-600">
              Анкета заполнена. Данные переданы врачу, он изучит их до начала
              приёма.
            </p>
          </motion.div>

          {/* Дополнительная информация */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="mt-8 p-4 bg-primary-50 rounded-xl text-left"
          >
            <p className="text-sm text-primary-800">
              <strong>Напоминание:</strong> Не забудьте взять с собой на приём
              паспорт и полис ОМС (при наличии).
            </p>
          </motion.div>

          {/* Можно закрыть */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
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
