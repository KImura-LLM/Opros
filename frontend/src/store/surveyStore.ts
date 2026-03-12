/**
 * Zustand Store для управления состоянием опроса
 */

import { create } from 'zustand'
import type {
  SurveyConfig,
  SurveyNode,
  AnswerData,
  AnimationDirection,
} from '@/types'

// ==========================================
// SessionStorage — сохраняем ТОЛЬКО идентификаторы сессии (не PII)
// sessionStorage безопаснее localStorage: очищается при закрытии вкладки
// ==========================================
const SESSION_STORAGE_KEY = 'opros_session'

export function saveSessionToStorage(token: string, sessionId: string): void {
  try {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ token, sessionId }))
  } catch {
    // Если sessionStorage недоступен — просто игнорируем
  }
}

export function getSessionFromStorage(): { token: string; sessionId: string } | null {
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed.token === 'string' && typeof parsed.sessionId === 'string') {
      return parsed
    }
  } catch {
    // Невалидные данные — очищаем
    clearSessionStorage()
  }
  return null
}

export function clearSessionStorage(): void {
  try {
    sessionStorage.removeItem(SESSION_STORAGE_KEY)
  } catch {
    // Игнорируем ошибки
  }
}

interface SurveyState {
  // Данные сессии
  sessionId: string | null
  patientName: string | null
  token: string | null
  expiresAt: string | null // ISO timestamp

  // Конфигурация опросника
  config: SurveyConfig | null

  // Текущее состояние
  currentNodeId: string
  answers: Record<string, AnswerData>
  history: string[]
  progress: number

  // UI состояние
  isLoading: boolean
  error: string | null
  animationDirection: AnimationDirection

  // Действия
  setSession: (sessionId: string, patientName?: string, expiresAt?: string) => void
  setToken: (token: string) => void
  setConfig: (config: SurveyConfig) => void
  setCurrentNode: (nodeId: string, direction?: AnimationDirection) => void
  setAnswer: (nodeId: string, answer: AnswerData) => void
  goBack: () => void
  setProgress: (progress: number) => void
  setLoading: (isLoading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void

  // Атомарное восстановление всей сессии после обновления страницы (один ре-рендер)
  restoreSession: (data: {
    config: SurveyConfig
    sessionId: string
    patientName?: string
    expiresAt?: string
    currentNodeId: string
    answers: Record<string, AnswerData>
    history: string[]
    progress: number
  }) => void

  // Геттеры
  getCurrentNode: () => SurveyNode | null
  getAnswer: (nodeId: string) => AnswerData | null
  canGoBack: () => boolean
}

const initialState = {
  sessionId: null,
  patientName: null,
  token: null,
  expiresAt: null,
  config: null,
  currentNodeId: 'welcome',
  answers: {},
  history: ['welcome'],
  progress: 0,
  isLoading: false,
  error: null,
  animationDirection: 'forward' as AnimationDirection,
}

export const useSurveyStore = create<SurveyState>()((set, get) => ({
  ...initialState,

  setSession: (sessionId: string, patientName?: string, expiresAt?: string) => {
    set({ 
      sessionId, 
      patientName: patientName || null, 
      expiresAt: expiresAt || null 
    })
    // Синхронизируем идентификаторы сессии в sessionStorage для восстановления при F5
    const token = get().token
    if (token && sessionId) {
      saveSessionToStorage(token, sessionId)
    }
  },

  setToken: (token: string) => {
    set({ token })
    // Синхронизируем в sessionStorage если сессия уже есть
    const sessionId = get().sessionId
    if (token && sessionId) {
      saveSessionToStorage(token, sessionId)
    }
  },

  setConfig: (config: SurveyConfig) =>
    set({
      config,
      currentNodeId: config.start_node,
      history: [config.start_node],
      // Сбрасываем прогресс при загрузке новой конфигурации,
      // чтобы не показывать устаревшее значение от предыдущей сессии
      progress: 0,
    }),

  setCurrentNode: (nodeId: string, direction: AnimationDirection = 'forward') =>
    set((state: SurveyState) => {
      const newHistory =
        direction === 'forward'
          ? [...state.history, nodeId]
          : state.history

      return {
        currentNodeId: nodeId,
        history: newHistory,
        animationDirection: direction,
      }
    }),

  setAnswer: (nodeId: string, answer: AnswerData) =>
    set((state: SurveyState) => ({
      answers: {
        ...state.answers,
        [nodeId]: answer,
      },
    })),

  goBack: () =>
    set((state: SurveyState) => {
      if (state.history.length <= 1) return state

      const newHistory = [...state.history]
      newHistory.pop() // Удаляем текущий
      const previousNode = newHistory[newHistory.length - 1]

      return {
        currentNodeId: previousNode,
        history: newHistory,
        animationDirection: 'backward' as AnimationDirection,
      }
    }),

  setProgress: (progress: number) => set({ progress }),

  setLoading: (isLoading: boolean) => set({ isLoading }),

  setError: (error: string | null) => set({ error }),

  reset: () => {
    clearSessionStorage()
    set(initialState)
  },

  // Атомарное восстановление: один set() = один ре-рендер, нет промежуточных состояний
  restoreSession: (data) => {
    set({
      config: data.config,
      sessionId: data.sessionId,
      patientName: data.patientName || null,
      expiresAt: data.expiresAt || null,
      currentNodeId: data.currentNodeId,
      answers: data.answers,
      history: data.history,
      progress: data.progress,
    })
  },

  getCurrentNode: () => {
    const state = get()
    if (!state.config) return null
    return (
      state.config.nodes.find((n: SurveyNode) => n.id === state.currentNodeId) || null
    )
  },

  getAnswer: (nodeId: string) => {
    const state = get()
    return state.answers[nodeId] || null
  },

  canGoBack: () => {
    const state = get()
    return state.history.length > 1
  },
}))
