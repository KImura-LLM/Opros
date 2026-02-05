/**
 * Карточки с множественным выбором (Multi Choice)
 */

import React from 'react'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import clsx from 'clsx'
import { getIcon } from '@/utils/icons'
import type { SurveyOption } from '@/types'

interface MultiChoiceProps {
  options: SurveyOption[]
  value: string[]
  onChange: (value: string[]) => void
  maxSelection?: number
}

export const MultiChoice: React.FC<MultiChoiceProps> = ({
  options,
  value,
  onChange,
  maxSelection,
}) => {
  const handleToggle = (optionValue: string) => {
    // Особая логика для "none" - сбрасывает все остальные
    if (optionValue === 'none') {
      onChange(['none'])
      return
    }

    // Если выбирается что-то кроме "none", убираем "none"
    let newValue = value.filter((v) => v !== 'none')

    if (newValue.includes(optionValue)) {
      // Убираем выбор
      newValue = newValue.filter((v) => v !== optionValue)
    } else {
      // Добавляем выбор
      if (maxSelection && newValue.length >= maxSelection) {
        return // Достигнут лимит
      }
      newValue = [...newValue, optionValue]
    }

    onChange(newValue)
  }

  return (
    <div className="space-y-3">
      {options.map((option, index) => {
        const optionValue = option.value || option.id
        const isSelected = value.includes(optionValue)
        const Icon = option.icon ? getIcon(option.icon) : null

        return (
          <motion.button
            key={option.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => handleToggle(optionValue)}
            className={clsx(
              'card-option flex items-center gap-4',
              isSelected && 'selected'
            )}
          >
            {/* Иконка */}
            {Icon && (
              <div
                className={clsx(
                  'w-10 h-10 rounded-lg flex items-center justify-center transition-colors',
                  isSelected
                    ? 'bg-primary-100 text-primary-600'
                    : 'bg-slate-100 text-slate-500'
                )}
              >
                <Icon className="w-5 h-5" />
              </div>
            )}

            {/* Текст */}
            <span className="flex-1 text-left text-slate-700 font-medium">
              {option.text}
            </span>

            {/* Чекбокс */}
            <div
              className={clsx(
                'checkbox-custom',
                isSelected && 'checked'
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
