/**
 * Карта тела для выбора локализации боли
 */

import React from 'react'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import clsx from 'clsx'
import type { SurveyOption } from '@/types'

interface BodyMapProps {
  options: SurveyOption[]
  value: string[]
  onChange: (value: string[]) => void
}

export const BodyMap: React.FC<BodyMapProps> = ({
  options,
  value,
  onChange,
}) => {
  const handleToggle = (optionValue: string) => {
    if (value.includes(optionValue)) {
      onChange(value.filter((v) => v !== optionValue))
    } else {
      onChange([...value, optionValue])
    }
  }

  // Позиции точек на карте тела (относительные, в процентах)
  const bodyPartPositions: Record<string, { top: string; left: string }> = {
    head: { top: '5%', left: '50%' },
    throat: { top: '18%', left: '50%' },
    chest: { top: '32%', left: '50%' },
    abdomen: { top: '48%', left: '50%' },
    back: { top: '40%', left: '75%' },
    joints: { top: '75%', left: '50%' },
  }

  return (
    <div className="space-y-6">
      {/* Упрощённая карта тела - используем список с визуальными индикаторами */}
      <div className="relative bg-slate-100 rounded-2xl p-4 min-h-[300px]">
        {/* Силуэт тела (SVG) */}
        <svg
          viewBox="0 0 100 200"
          className="w-full h-[250px] mx-auto"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
        >
          {/* Голова */}
          <circle cx="50" cy="20" r="12" className="fill-slate-200 stroke-slate-300" />
          {/* Шея */}
          <line x1="50" y1="32" x2="50" y2="40" className="stroke-slate-300" />
          {/* Туловище */}
          <ellipse cx="50" cy="70" rx="20" ry="30" className="fill-slate-200 stroke-slate-300" />
          {/* Руки */}
          <line x1="30" y1="50" x2="15" y2="90" className="stroke-slate-300" strokeWidth="6" strokeLinecap="round" />
          <line x1="70" y1="50" x2="85" y2="90" className="stroke-slate-300" strokeWidth="6" strokeLinecap="round" />
          {/* Ноги */}
          <line x1="40" y1="100" x2="35" y2="170" className="stroke-slate-300" strokeWidth="8" strokeLinecap="round" />
          <line x1="60" y1="100" x2="65" y2="170" className="stroke-slate-300" strokeWidth="8" strokeLinecap="round" />
        </svg>

        {/* Интерактивные точки */}
        {options.map((option) => {
          const position = bodyPartPositions[option.value]
          const isSelected = value.includes(option.value)

          if (!position) return null

          return (
            <motion.button
              key={option.id}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => handleToggle(option.value)}
              style={{
                position: 'absolute',
                top: position.top,
                left: position.left,
                transform: 'translate(-50%, -50%)',
              }}
              className={clsx(
                'w-10 h-10 rounded-full flex items-center justify-center',
                'transition-all duration-200 shadow-lg',
                isSelected
                  ? 'bg-red-500 text-white scale-110'
                  : 'bg-white text-slate-400 hover:bg-primary-50 hover:text-primary-600'
              )}
            >
              {isSelected ? (
                <Check className="w-5 h-5" />
              ) : (
                <span className="text-xs font-bold">+</span>
              )}
            </motion.button>
          )
        })}
      </div>

      {/* Легенда / Выбранные области */}
      <div className="space-y-2">
        <p className="text-sm text-slate-500">Выбранные области:</p>
        <div className="flex flex-wrap gap-2">
          {options.map((option) => {
            const isSelected = value.includes(option.value)
            return (
              <button
                key={option.id}
                onClick={() => handleToggle(option.value)}
                className={clsx(
                  'px-3 py-1.5 rounded-full text-sm font-medium transition-all',
                  isSelected
                    ? 'bg-red-100 text-red-700 border border-red-200'
                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                )}
              >
                {option.text}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
