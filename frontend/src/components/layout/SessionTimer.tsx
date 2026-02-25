/**
 * Компонент таймера обратного отсчёта до истечения сессии
 */

import { useEffect, useState } from 'react'

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

  // Таймер работает в фоне (onExpire срабатывает при истечении),
  // но визуальное отображение скрыто
  return null
}
