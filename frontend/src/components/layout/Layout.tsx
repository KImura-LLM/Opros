/**
 * Layout компоненты
 */

import React from 'react'
import { X, Plus } from 'lucide-react'
import { motion } from 'framer-motion'

// Header с логотипом и кнопкой закрытия
interface HeaderProps {
  onClose?: () => void
  showClose?: boolean
}

export const Header: React.FC<HeaderProps> = ({
  onClose,
  showClose = true,
}) => {
  return (
    <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-100">
      <div className="max-w-lg mx-auto px-4 h-14 flex items-center justify-between">
        {/* Логотип */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <Plus className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-slate-800">Ваша Клиника</span>
        </div>

        {/* Кнопка закрытия */}
        {showClose && onClose && (
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 transition-colors"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>
    </header>
  )
}

// Progress Bar
interface ProgressBarProps {
  progress: number // 0-100
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ progress }) => {
  return (
    <div className="bg-white border-b border-slate-100">
      <div className="max-w-lg mx-auto px-4 py-2">
        <div className="progress-bar">
          <motion.div
            className="progress-bar-fill"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        <p className="text-xs text-slate-400 mt-1 text-right">
          {Math.round(progress)}% завершено
        </p>
      </div>
    </div>
  )
}

// Footer с кнопками навигации
interface FooterProps {
  onBack?: () => void
  onNext?: () => void
  nextLabel?: string
  backLabel?: string
  nextDisabled?: boolean
  showBack?: boolean
  isLoading?: boolean
}

export const Footer: React.FC<FooterProps> = ({
  onBack,
  onNext,
  nextLabel = 'Далее',
  backLabel = 'Назад',
  nextDisabled = false,
  showBack = true,
  isLoading = false,
}) => {
  return (
    <footer className="sticky bottom-0 bg-white/80 backdrop-blur-md border-t border-slate-100">
      <div className="max-w-lg mx-auto px-4 py-4 flex gap-3">
        {showBack && onBack && (
          <button
            onClick={onBack}
            className="btn-secondary flex-1"
            disabled={isLoading}
          >
            {backLabel}
          </button>
        )}
        {onNext && (
          <button
            onClick={onNext}
            className="btn-primary flex-1"
            disabled={nextDisabled || isLoading}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Загрузка...
              </span>
            ) : (
              nextLabel
            )}
          </button>
        )}
      </div>
    </footer>
  )
}

// Основной контейнер страницы
interface PageContainerProps {
  children: React.ReactNode
}

export const PageContainer: React.FC<PageContainerProps> = ({ children }) => {
  return (
    <main className="flex-1 overflow-auto">
      <div className="max-w-lg mx-auto px-4 py-6">{children}</div>
    </main>
  )
}
