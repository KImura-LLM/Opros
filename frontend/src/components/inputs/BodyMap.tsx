/**
 * Карта тела для выбора локализации боли
 * Изображение контурного силуэта человека с наложенными интерактивными зонами
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import clsx from 'clsx'
import type { SurveyOption } from '@/types'

/* Импорт изображения силуэта тела */
import bodyOutlineImg from '/images/body-outline.png'

interface BodyMapProps {
  options: SurveyOption[]
  value: string[]
  onChange: (value: string[]) => void
}

/* Цвета */
const ZONE_ACTIVE = '#ef4444'
const ZONE_ACTIVE_FILL = 'rgba(254, 202, 202, 0.6)'
const ZONE_HOVER_FILL = 'rgba(219, 234, 254, 0.5)'

/**
 * Определения интерактивных зон поверх изображения.
 * Координаты заданы в процентах относительно размеров изображения.
 * Каждая зона — SVG path в viewBox 100x100 (проценты).
 */
interface BodyZone {
  id: string
  label: string
  /* SVG path в viewBox 0 0 1000 1000 для точности */
  path: string
  /* Координаты центра метки (галочки) в viewBox */
  cx: number
  cy: number
}

const BODY_ZONES: BodyZone[] = [
  {
    id: 'head',
    label: 'Голова',
    // Эллиптическая зона вокруг головы
    path: 'M 500 28 C 440 28, 410 55, 410 85 C 410 118, 435 145, 500 145 C 565 145, 590 118, 590 85 C 590 55, 560 28, 500 28 Z',
    cx: 500,
    cy: 85,
  },
  {
    id: 'throat',
    label: 'Горло',
    // Зона горла / шеи
    path: 'M 448 145 L 552 145 L 555 195 L 445 195 Z',
    cx: 500,
    cy: 170,
  },
  {
    id: 'chest',
    label: 'Грудная клетка',
    // Грудная клетка — от плеч до середины торса
    path: 'M 375 195 L 625 195 L 618 410 L 382 410 Z',
    cx: 500,
    cy: 300,
  },
  {
    id: 'abdomen',
    label: 'Живот',
    // Живот — от середины торса до пояса
    path: 'M 382 410 L 618 410 L 610 560 L 390 560 Z',
    cx: 500,
    cy: 485,
  },
  {
    id: 'back',
    label: 'Поясница',
    // Поясница / таз — нижняя часть торса
    path: 'M 390 560 L 610 560 L 595 660 L 405 660 Z',
    cx: 500,
    cy: 610,
  },
  {
    id: 'joints',
    label: 'Суставы / Конечности',
    // Левая рука
    path: `
      M 375 195 L 310 210 C 270 230, 235 270, 210 330
      C 190 380, 175 420, 165 470
      C 155 510, 150 540, 155 560
      C 155 570, 160 578, 170 580
      L 195 575 C 210 568, 215 558, 220 540
      C 228 505, 240 470, 250 440
      C 265 400, 280 370, 300 340
      C 315 320, 330 305, 345 290
      L 382 410 L 375 195 Z

      M 625 195 L 690 210 C 730 230, 765 270, 790 330
      C 810 380, 825 420, 835 470
      C 845 510, 850 540, 845 560
      C 845 570, 840 578, 830 580
      L 805 575 C 790 568, 785 558, 780 540
      C 772 505, 760 470, 750 440
      C 735 400, 720 370, 700 340
      C 685 320, 670 305, 655 290
      L 618 410 L 625 195 Z

      M 405 660 L 390 700 C 382 750, 378 800, 375 850
      C 373 890, 375 920, 385 950
      C 390 965, 400 970, 415 970
      L 440 965 C 455 960, 460 950, 462 935
      C 465 910, 468 875, 470 840
      C 472 800, 478 760, 485 720
      L 500 660 L 405 660 Z

      M 595 660 L 610 700 C 618 750, 622 800, 625 850
      C 627 890, 625 920, 615 950
      C 610 965, 600 970, 585 970
      L 560 965 C 545 960, 540 950, 538 935
      C 535 910, 532 875, 530 840
      C 528 800, 522 760, 515 720
      L 500 660 L 595 660 Z
    `,
    cx: 500,
    cy: 820,
  },
]

export const BodyMap: React.FC<BodyMapProps> = ({
  options,
  value,
  onChange,
}) => {
  const [hoveredZone, setHoveredZone] = useState<string | null>(null)

  const handleToggle = (optionValue: string) => {
    if (value.includes(optionValue)) {
      onChange(value.filter((v) => v !== optionValue))
    } else {
      onChange([...value, optionValue])
    }
  }

  const getZoneFill = (zone: string) => {
    if (value.includes(zone)) return ZONE_ACTIVE_FILL
    if (hoveredZone === zone) return ZONE_HOVER_FILL
    return 'transparent'
  }

  const getZoneStroke = (zone: string) => {
    if (value.includes(zone)) return ZONE_ACTIVE
    if (hoveredZone === zone) return '#3b82f6'
    return 'transparent'
  }

  return (
    <div className="space-y-6">
      {/* Карта тела — изображение с наложенными интерактивными зонами */}
      <div className="relative bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
        <div className="relative w-full max-w-[320px] mx-auto">
          {/* Фоновое изображение силуэта тела */}
          <img
            src={bodyOutlineImg}
            alt="Контур тела человека"
            className="w-full h-auto select-none pointer-events-none"
            draggable={false}
          />

          {/* SVG-оверлей с интерактивными зонами поверх картинки */}
          <svg
            viewBox="0 0 1000 1000"
            className="absolute inset-0 w-full h-full"
            xmlns="http://www.w3.org/2000/svg"
            preserveAspectRatio="xMidYMid meet"
          >
            {BODY_ZONES.map((zone) => (
              <g key={zone.id}>
                <path
                  d={zone.path}
                  fill={getZoneFill(zone.id)}
                  stroke={getZoneStroke(zone.id)}
                  strokeWidth={value.includes(zone.id) ? 3 : 2}
                  style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                  onClick={() => handleToggle(zone.id)}
                  onMouseEnter={() => setHoveredZone(zone.id)}
                  onMouseLeave={() => setHoveredZone(null)}
                  fillRule="evenodd"
                />
                {/* Галочка при выборе зоны */}
                {value.includes(zone.id) && (
                  <g>
                    <circle cx={zone.cx} cy={zone.cy} r={22} fill="white" opacity={0.95} />
                    <path
                      d={`M ${zone.cx - 12} ${zone.cy} L ${zone.cx - 4} ${zone.cy + 8} L ${zone.cx + 12} ${zone.cy - 8}`}
                      stroke={ZONE_ACTIVE}
                      strokeWidth="5"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </g>
                )}
              </g>
            ))}
          </svg>
        </div>
      </div>

      {/* Кнопки выбора */}
      <div className="space-y-2">
        <p className="text-sm text-slate-500">Выберите области боли:</p>
        <div className="flex flex-wrap gap-2">
          {options.map((option) => {
            const isSelected = value.includes(option.value)
            return (
              <motion.button
                key={option.id}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleToggle(option.value)}
                className={clsx(
                  'px-4 py-2 rounded-xl text-sm font-medium transition-all border',
                  isSelected
                    ? 'bg-red-500 text-white border-red-400 shadow-md shadow-red-200'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-red-300 hover:text-red-600'
                )}
              >
                {isSelected && <Check className="w-3.5 h-3.5 inline-block mr-1 -mt-0.5" />}
                {option.text}
              </motion.button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
