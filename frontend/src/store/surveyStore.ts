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

  setSession: (sessionId: string, patientName?: string, expiresAt?: string) =>
    set({ 
      sessionId, 
      patientName: patientName || null, 
      expiresAt: expiresAt || null 
    }),

  setToken: (token: string) => set({ token }),

  setConfig: (config: SurveyConfig) =>
    set({
      config,
      currentNodeId: config.start_node,
      history: [config.start_node],
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

  reset: () => set(initialState),

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
