/**
 * Страница ошибки
 */

import React from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertCircle } from 'lucide-react'
import { Branding } from '@/components/layout/Branding'

const ErrorPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const errorMessage = searchParams.get('message') || 'Произошла ошибка'

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
          className="text-center max-w-md"
        >
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>

          <h1 className="mt-4 text-xl font-semibold text-slate-900">
            Что-то пошло не так
          </h1>

          <p className="mt-2 text-slate-600">{errorMessage}</p>

          <div className="mt-6 p-4 bg-slate-100 rounded-xl text-left">
            <p className="text-sm text-slate-600">
              Если проблема повторяется, пожалуйста, свяжитесь с клиникой по
              телефону или попросите отправить вам новую ссылку.
            </p>
          </div>
        </motion.div>
      </main>
    </div>
  )
}

export default ErrorPage
