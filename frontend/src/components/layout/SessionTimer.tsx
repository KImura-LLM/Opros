/**
 * Компонент таймера обратного отсчёта до истечения сессии.
 * Работает в фоне — визуально не отображается.
 */

import { useEffect } from 'react'

interface SessionTimerProps {
  expiresAt: string // ISO timestamp
  onExpire?: () => void
}

export const SessionTimer = ({ expiresAt, onExpire }: SessionTimerProps) => {
  useEffect(() => {
    const calculateTimeLeft = () => {
      const diff = new Date(expiresAt).getTime() - Date.now()
      return diff > 0 ? diff : 0
    }

    // Обновление каждую секунду — вызывает onExpire при истечении
    const timer = setInterval(() => {
      if (calculateTimeLeft() === 0 && onExpire) {
        onExpire()
      }
    }, 1000)

    return () => clearInterval(timer)
  }, [expiresAt, onExpire])

  // Таймер работает в фоне, визуально не отображается
  return null
}
