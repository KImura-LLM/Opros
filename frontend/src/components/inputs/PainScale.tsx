/**
 * Слайдер для оценки интенсивности боли (1-10)
 */

import React from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'

interface PainScaleProps {
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
}

export const PainScale: React.FC<PainScaleProps> = ({
  value,
  onChange,
  min = 1,
  max = 10,
}) => {
  const getColor = (val: number) => {
    if (val <= 3) return 'bg-green-500'
    if (val <= 6) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getLabel = (val: number) => {
    if (val <= 2) return 'Едва заметная'
    if (val <= 4) return 'Слабая'
    if (val <= 6) return 'Умеренная'
    if (val <= 8) return 'Сильная'
    return 'Невыносимая'
  }

  return (
    <div className="space-y-6">
      {/* Значение */}
      <div className="text-center">
        <motion.div
          key={value}
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          className={clsx(
            'inline-flex items-center justify-center w-20 h-20 rounded-full text-white text-3xl font-bold',
            getColor(value)
          )}
        >
          {value}
        </motion.div>
        <p className="mt-2 text-slate-600 font-medium">{getLabel(value)}</p>
      </div>

      {/* Слайдер */}
      <div className="space-y-2">
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value))}
          className="pain-slider w-full"
        />
        <div className="flex justify-between text-xs text-slate-400">
          <span>{min}</span>
          <span>{max}</span>
        </div>
      </div>

      {/* Легенда */}
      <div className="flex justify-between text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-slate-500">Слабая</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className="text-slate-500">Умеренная</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-slate-500">Сильная</span>
        </div>
      </div>
    </div>
  )
}
