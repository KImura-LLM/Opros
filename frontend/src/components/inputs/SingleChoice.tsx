/**
 * Карточка варианта ответа (Single Choice)
 */

import React from 'react'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import clsx from 'clsx'
import type { SurveyOption } from '@/types'

interface SingleChoiceProps {
  options: SurveyOption[]
  value: string | null
  onChange: (value: string) => void
}

export const SingleChoice: React.FC<SingleChoiceProps> = ({
  options,
  value,
  onChange,
}) => {
  return (
    <div className="space-y-3">
      {options.map((option, index) => {
        const optionValue = option.value || option.id
        const isSelected = value === optionValue

        return (
          <motion.button
            key={option.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onChange(optionValue)}
            className={clsx(
              'card-option flex items-center gap-4',
              isSelected && 'selected'
            )}
          >
            {/* Текст */}
            <span className="flex-1 text-left text-slate-700 font-medium">
              {option.text}
            </span>

            {/* Индикатор выбора */}
            <div
              className={clsx(
                'w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all',
                isSelected
                  ? 'bg-primary-600 border-primary-600'
                  : 'border-slate-300'
              )}
            >
              {isSelected && <Check className="w-4 h-4 text-white" />}
            </div>
          </motion.button>
        )
      })}
    </div>
  )
}
