/**
 * Компонент таймера обратного отсчёта до истечения сессии
 */

import { useEffect, useState } from 'react'
import { Clock } from 'lucide-react'

interface SessionTimerProps {
  expiresAt: string // ISO timestamp
  onExpire?: () => void
}

export const SessionTimer = ({ expiresAt, onExpire }: SessionTimerProps) => {
  const [timeLeft, setTimeLeft] = useState<number>(0)

  useEffect(() => {
    const calculateTimeLeft = () => {
      const now = new Date().getTime()
      const expiry = new Date(expiresAt).getTime()
      const diff = expiry - now

      return diff > 0 ? diff : 0
    }

    // Обновление каждую секунду
    const timer = setInterval(() => {
      const remaining = calculateTimeLeft()
      setTimeLeft(remaining)

      if (remaining === 0 && onExpire) {
        onExpire()
      }
    }, 1000)

    // Начальное значение
    setTimeLeft(calculateTimeLeft())

    return () => clearInterval(timer)
  }, [expiresAt, onExpire])

  // Форматирование времени
  const formatTime = (ms: number): string => {
    const totalSeconds = Math.floor(ms / 1000)
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  // Определение цвета в зависимости от оставшегося времени
  const getColor = () => {
    const totalSeconds = Math.floor(timeLeft / 1000)
    if (totalSeconds < 300) return 'text-red-600' // < 5 минут
    if (totalSeconds < 900) return 'text-yellow-600' // < 15 минут
    return 'text-gray-600'
  }

  // Таймер работает в фоне (onExpire срабатывает при истечении),
  // но визуальное отображение скрыто
  return null
}
