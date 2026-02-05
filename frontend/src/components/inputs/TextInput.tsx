/**
 * Текстовое поле ввода
 */

import React from 'react'

interface TextInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  label?: string
  multiline?: boolean
  rows?: number
}

export const TextInput: React.FC<TextInputProps> = ({
  value,
  onChange,
  placeholder,
  label,
  multiline = false,
  rows = 3,
}) => {
  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
          className="input-field resize-none"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="input-field"
        />
      )}
    </div>
  )
}

/**
 * Числовое поле ввода
 */

interface NumberInputProps {
  value: number | null
  onChange: (value: number | null) => void
  placeholder?: string
  label?: string
  min?: number
  max?: number
}

export const NumberInput: React.FC<NumberInputProps> = ({
  value,
  onChange,
  placeholder,
  label,
  min,
  max,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    if (val === '') {
      onChange(null)
    } else {
      const num = parseInt(val)
      if (!isNaN(num)) {
        if (min !== undefined && num < min) return
        if (max !== undefined && num > max) return
        onChange(num)
      }
    }
  }

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <input
        type="number"
        inputMode="numeric"
        value={value ?? ''}
        onChange={handleChange}
        placeholder={placeholder}
        min={min}
        max={max}
        className="input-field"
      />
    </div>
  )
}
