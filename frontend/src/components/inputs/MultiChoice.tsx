/**
 * Карточки с множественным выбором (Multi Choice)
 */

import React from 'react'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import clsx from 'clsx'
import type { SurveyOption } from '@/types'

interface MultiChoiceProps {
  options: SurveyOption[]
  value: string[]
  onChange: (value: string[]) => void
  maxSelection?: number
  // Значение варианта-исключения: при его выборе снимаются все остальные,
  // и наоборот — при выборе любого другого этот вариант снимается
  exclusiveOption?: string
}

export const MultiChoice: React.FC<MultiChoiceProps> = ({
  options,
  value,
  onChange,
  maxSelection,
  exclusiveOption,
}) => {
  const handleToggle = (optionValue: string) => {
    // Если выбирается вариант-исключение — сбрасываем всё остальное
    if (exclusiveOption && optionValue === exclusiveOption) {
      onChange([exclusiveOption])
      return
    }

    // Если выбирается что-то другое — убираем вариант-исключение
    let newValue = exclusiveOption
      ? value.filter((v) => v !== exclusiveOption)
      : [...value]

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
