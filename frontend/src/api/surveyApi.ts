/**
 * API клиент для взаимодействия с Backend
 */

import type {
  TokenValidationResponse,
  SurveyStartResponse,
  SurveyAnswerResponse,
  SurveyCompleteResponse,
  SurveyProgressSnapshot,
  AnswerData,
} from '@/types'
import { useSurveyStore } from '@/store/surveyStore'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

/**
 * Получение токена сессии из store (для привязки запросов к сессии)
 */
function getSessionToken(): string | null {
  try {
    return useSurveyStore.getState().token
  } catch {
    return null
  }
}

/**
 * Базовый fetch с обработкой ошибок
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`

  // Добавляем токен сессии для изоляции доступа
  const sessionToken = getSessionToken()
  const extraHeaders: Record<string, string> = {}
  if (sessionToken) {
    extraHeaders['X-Session-Token'] = sessionToken
  }

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...extraHeaders,
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP error ${response.status}`)
  }

  return response.json()
}

/**
 * Валидация JWT токена
 */
export async function validateToken(
  token: string
): Promise<TokenValidationResponse> {
  return apiFetch<TokenValidationResponse>(
    `/auth/validate?token=${encodeURIComponent(token)}`
  )
}

/**
 * Начало опроса
 */
export async function startSurvey(
  token: string,
  consentGiven: boolean
): Promise<SurveyStartResponse> {
  return apiFetch<SurveyStartResponse>('/survey/start', {
    method: 'POST',
    body: JSON.stringify({
      token,
      consent_given: consentGiven,
    }),
  })
}

/**
 * Отправка ответа
 */
export async function submitAnswer(
  sessionId: string,
  nodeId: string,
  answerData: AnswerData,
  durationSeconds?: number
): Promise<SurveyAnswerResponse> {
  return apiFetch<SurveyAnswerResponse>('/survey/answer', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      node_id: nodeId,
      answer_data: answerData,
      ...(durationSeconds !== undefined && { duration_seconds: durationSeconds }),
    }),
  })
}

/**
 * Получение прогресса
 */
export async function getProgress(sessionId: string): Promise<SurveyProgressSnapshot & {
  session_id: string
}> {
  return apiFetch(`/survey/progress/${sessionId}`)
}

/**
 * Завершение опроса
 */
export async function completeSurvey(
  sessionId: string
): Promise<SurveyCompleteResponse> {
  return apiFetch<SurveyCompleteResponse>('/survey/complete', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
    }),
  })
}

/**
 * Возврат на предыдущий вопрос
 */
export async function goBackApi(
  sessionId: string
): Promise<SurveyProgressSnapshot & { success: boolean }> {
  return apiFetch(`/survey/back`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}
