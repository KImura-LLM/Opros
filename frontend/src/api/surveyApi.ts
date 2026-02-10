/**
 * API клиент для взаимодействия с Backend
 */

import type {
  TokenValidationResponse,
  SurveyStartResponse,
  SurveyAnswerResponse,
  SurveyCompleteResponse,
  SurveyConfig,
  AnswerData,
} from '@/types'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

/**
 * Базовый fetch с обработкой ошибок
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
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
 * Получение конфигурации опросника
 */
export async function getSurveyConfig(): Promise<{ json_config: SurveyConfig }> {
  return apiFetch<{ json_config: SurveyConfig }>('/survey/config')
}

/**
 * Отправка ответа
 */
export async function submitAnswer(
  sessionId: string,
  nodeId: string,
  answerData: AnswerData
): Promise<SurveyAnswerResponse> {
  return apiFetch<SurveyAnswerResponse>('/survey/answer', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      node_id: nodeId,
      answer_data: answerData,
    }),
  })
}

/**
 * Получение прогресса
 */
export async function getProgress(sessionId: string): Promise<{
  session_id: string
  current_node: string
  answers: Record<string, AnswerData>
  history: string[]
  progress_percent: number
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
): Promise<{ success: boolean; current_node: string }> {
  return apiFetch(`/survey/back`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}
