/**
 * Страница прохождения опроса
 */

import React, { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { useSurveyStore, getSessionFromStorage, clearSessionStorage } from '@/store'
import { submitAnswer, completeSurvey, goBackApi, startSurvey, getProgress } from '@/api'
import { Header, ProgressBar, Footer, PageContainer, SessionTimer } from '@/components/layout'
import {
  SingleChoice,
  MultiChoice,
  PainScale,
  BodyMap,
  TextInput,
  NumberInput,
} from '@/components/inputs'
import type { AnswerData, SurveyNode } from '@/types'

const SurveyPage: React.FC = () => {
  const navigate = useNavigate()
  const {
    sessionId,
    config,
    currentNodeId,
    answers,
    progress,
    animationDirection,
    expiresAt,
    setToken,
    setCurrentNode,
    setAnswer,
    setProgress,
    goBack,
    canGoBack,
    restoreSession,
  } = useSurveyStore()

  const [currentAnswer, setCurrentAnswer] = useState<AnswerData>({})
  const [isLoading, setIsLoading] = useState(false)
  // Флаг: идёт восстановление сессии после обновления страницы
  const [isRestoring, setIsRestoring] = useState(!config || !sessionId)
  // Защита от двойного вызова (React Strict Mode монтирует эффект дважды)
  const restoreAttempted = useRef(false)
  // Трекинг времени: запоминаем момент показа вопроса
  const questionStartTime = useRef<number>(Date.now())

  // ==========================================
  // Восстановление сессии при обновлении страницы (F5 / обрыв сети)
  // ==========================================
  useEffect(() => {
    // Данные уже есть (нормальный переход с HomePage) — восстановление не нужно
    if (config && sessionId) {
      setIsRestoring(false)
      return
    }

    // React Strict Mode запускает эффект дважды — блокируем повторный запуск
    if (restoreAttempted.current) return
    restoreAttempted.current = true

    const saved = getSessionFromStorage()
    if (!saved) {
      navigate('/', { replace: true })
      return
    }

    // Используем IIFE чтобы не возвращать Promise из useEffect
    ;(async () => {
      try {
        // Устанавливаем токен заранее — нужен в заголовке X-Session-Token
        setToken(saved.token)

        // Бэкенд вернёт существующую сессию (не создаст новую)
        const startResp = await startSurvey(saved.token, true)

        // Получаем текущий прогресс: узел, историю, ответы
        const progressResp = await getProgress(String(startResp.session_id))

        // Атомарный update всего состояния — один ре-рендер вместо нескольких
        restoreSession({
          config: startResp.survey_config,
          sessionId: String(startResp.session_id),
          patientName: startResp.patient_name,
          expiresAt: startResp.expires_at,
          currentNodeId: progressResp.current_node,
          answers: progressResp.answers || {},
          history: progressResp.history || [],
          progress: progressResp.progress_percent,
        })

        setIsRestoring(false)
      } catch (err) {
        console.error('Не удалось восстановить сессию:', err)
        clearSessionStorage()
        navigate('/', { replace: true })
      }
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Получение текущего узла
  const currentNode: SurveyNode | null = config?.nodes.find(
    (n) => n.id === currentNodeId
  ) || null

  // Загрузка сохранённого ответа при смене узла
  useEffect(() => {
    if (isRestoring) return
    // Сброс таймера времени ответа при переходе на новый вопрос
    questionStartTime.current = Date.now()
    const savedAnswer = answers[currentNodeId]
    if (savedAnswer) {
      setCurrentAnswer(savedAnswer)
    } else {
      // Инициализация дефолтных значений для body_map
      // чтобы PainScale отображал значение, совпадающее с состоянием
      if (currentNode?.type === 'body_map') {
        setCurrentAnswer({ locations: [], intensity: 5 })
      } else {
        setCurrentAnswer({})
      }
    }
  }, [currentNodeId, answers, isRestoring])

  // Проверка, можно ли продолжить
  const canProceed = useCallback(() => {
    if (!currentNode) return false
    
    // Info screen - всегда можно
    if (currentNode.type === 'info_screen') return true
    
    // Single choice
    if (currentNode.type === 'single_choice') {
      return !!currentAnswer.selected
    }
    
    // Multi choice
    if (currentNode.type === 'multi_choice' || currentNode.type === 'multi_choice_with_input') {
      const selected = currentAnswer.selected as string[] | undefined
      return Array.isArray(selected) && selected.length > 0
    }
    
    // Body map
    if (currentNode.type === 'body_map') {
      if (!currentNode.required) return true
      const locations = currentAnswer.locations as string[] | undefined
      const intensity = currentAnswer.intensity
      return Array.isArray(locations) && locations.length > 0 && intensity !== undefined
    }
    
    // Scale 1-10 / slider
    if (currentNode.type === 'scale_1_10' || currentNode.type === 'slider') {
      return currentAnswer.value !== undefined && currentAnswer.value !== null
    }
    
    // Text input
    if (currentNode.type === 'text_input') {
      const text = currentAnswer.text as string | undefined
      return currentNode.required ? !!text && text.trim().length > 0 : true
    }
    
    // Number input
    if (currentNode.type === 'number_input') {
      return currentAnswer.value !== undefined && currentAnswer.value !== null
    }

    // Consent screen
    if (currentNode.type === 'consent_screen') {
      return (currentAnswer.selected as unknown) === true
    }
    
    return true
  }, [currentNode, currentAnswer])

  // Определение следующего узла
  const getNextNode = useCallback(() => {
    if (!currentNode || !config) return null
    
    const logic = currentNode.logic || []
    
    // Проверка условий
    for (const rule of logic) {
      if (rule.default) continue
      
      const condition = rule.condition
      if (condition) {
        // Простая проверка условий
        if (condition.includes('==')) {
          const [, expectedValue] = condition.split('==').map(s => s.trim().replace(/'/g, ''))
          if (currentAnswer.selected === expectedValue) {
            return rule.next_node
          }
        }
        
        if (condition.includes('contains')) {
          const [, expectedValue] = condition.split('contains').map(s => s.trim().replace(/'/g, ''))
          const selected = currentAnswer.selected as string[] | undefined
          if (Array.isArray(selected) && selected.includes(expectedValue)) {
            return rule.next_node
          }
        }
      }
    }
    
    // Default переход
    for (const rule of logic) {
      if (rule.default) {
        return rule.next_node
      }
    }
    
    return null
  }, [currentNode, config, currentAnswer])

  // Обработка нажатия "Далее"
  const handleNext = async () => {
    if (!currentNode || !sessionId) return
    
    // Если это финальный узел — мгновенная навигация, сервер догонит в фоне
    if (currentNode.is_final) {
      // Сохраняем ответ локально
      if (currentNode.type !== 'info_screen') {
        setAnswer(currentNodeId, currentAnswer)
      }

      // Fire-and-forget: отправляем последний ответ + завершение, не блокируя UI
      if (currentNode.type !== 'info_screen') {
        const elapsed = Math.round((Date.now() - questionStartTime.current) / 1000)
        submitAnswer(sessionId, currentNodeId, currentAnswer, elapsed).catch((err) =>
          console.warn('Фоновая отправка ответа:', err)
        )
      }
      completeSurvey(sessionId).catch((err) =>
        console.warn('Фоновое завершение опроса:', err)
      )

      // Мгновенный переход на экран завершения
      navigate('/complete')
      return
    }

    setIsLoading(true)
    
    try {
      // Сохраняем ответ локально
      if (currentNode.type !== 'info_screen') {
        setAnswer(currentNodeId, currentAnswer)
      }
      
      // Отправляем на сервер
      if (currentNode.type !== 'info_screen' && sessionId) {
        const elapsed = Math.round((Date.now() - questionStartTime.current) / 1000)
        const response = await submitAnswer(sessionId, currentNodeId, currentAnswer, elapsed)
        setProgress(response.progress)
        
        if (response.next_node) {
          setCurrentNode(response.next_node, 'forward')
          return
        }
      }
      
      // Локальное определение следующего узла
      const nextNodeId = getNextNode()
      
      if (nextNodeId) {
        setCurrentNode(nextNodeId, 'forward')
      }
    } catch (error) {
      console.error('Error submitting answer:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Обработка нажатия "Назад"
  const handleBack = async () => {
    if (!sessionId) return
    try {
      const response = await goBackApi(sessionId)
      if (response.success) {
        goBack()
      }
    } catch (error) {
      console.error('Error going back:', error)
      // Fallback: локальный goBack если сервер недоступен
      goBack()
    }
  }

  // Обработка истечения времени сессии
  const handleSessionExpired = useCallback(() => {
    alert('Время сессии истекло. Опрос будет автоматически завершён.')
    navigate('/')
  }, [navigate])

  // Закрытие опроса
  const handleClose = () => {
    if (confirm('Вы уверены, что хотите закрыть опрос? Прогресс будет сохранён.')) {
      navigate('/')
    }
  }

  // Рендер контента вопроса
  const renderContent = () => {
    if (!currentNode) return null

    switch (currentNode.type) {
      case 'info_screen':
        return (
          <div className="text-center py-8">
            <h1 className="text-2xl font-bold text-slate-900">
              {currentNode.question_text}
            </h1>
            {currentNode.description && (
              <p className="mt-4 text-slate-600">{currentNode.description}</p>
            )}
          </div>
        )

      case 'single_choice':
        return (
          <div className="space-y-6">
            <SingleChoice
              options={currentNode.options || []}
              value={(currentAnswer.selected as string) || null}
              onChange={(value) => setCurrentAnswer((prev) => ({ ...prev, selected: value }))}
            />
            
            {/* Дополнительные поля для single_choice */}
            {currentNode.additional_fields?.map((field) => {
              if (field.type === 'text') {
                return (
                  <TextInput
                    key={field.id}
                    label={field.label}
                    placeholder={field.placeholder}
                    value={(currentAnswer[field.id] as string) || ''}
                    onChange={(value) =>
                      setCurrentAnswer((prev) => ({ ...prev, [field.id]: value }))
                    }
                  />
                )
              }
              if (field.type === 'number') {
                return (
                  <NumberInput
                    key={field.id}
                    label={field.label}
                    placeholder={field.placeholder}
                    value={(currentAnswer[field.id] as number) ?? null}
                    onChange={(value) =>
                      setCurrentAnswer((prev) => ({ ...prev, [field.id]: value }))
                    }
                    min={field.min}
                    max={field.max}
                  />
                )
              }
              return null
            })}
          </div>
        )

      case 'multi_choice':
      case 'multi_choice_with_input':
        return (
          <div className="space-y-6">
            <MultiChoice
              options={currentNode.options || []}
              value={(currentAnswer.selected as string[]) || []}
              onChange={(value) =>
                setCurrentAnswer((prev) => ({ ...prev, selected: value }))
              }
              exclusiveOption={currentNode.exclusive_option}
            />
            
            {/* Дополнительные поля */}
            {currentNode.additional_fields?.map((field) => {
              if (field.type === 'number') {
                return (
                  <NumberInput
                    key={field.id}
                    label={field.label}
                    placeholder={field.placeholder}
                    value={(currentAnswer[field.id] as number) ?? null}
                    onChange={(value) =>
                      setCurrentAnswer((prev) => ({ ...prev, [field.id]: value }))
                    }
                    min={field.min}
                    max={field.max}
                  />
                )
              }
              if (field.type === 'text') {
                return (
                  <TextInput
                    key={field.id}
                    label={field.label}
                    placeholder={field.placeholder}
                    value={(currentAnswer[field.id] as string) || ''}
                    onChange={(value) =>
                      setCurrentAnswer((prev) => ({ ...prev, [field.id]: value }))
                    }
                  />
                )
              }
              return null
            })}
          </div>
        )

      case 'body_map':
        return (
          <div className="space-y-6">
            <BodyMap
              options={currentNode.options || []}
              value={(currentAnswer.locations as string[]) || []}
              onChange={(value) =>
                setCurrentAnswer((prev) => ({ ...prev, locations: value }))
              }
            />
            
            <div className="pt-4 border-t border-slate-200">
              <p className="text-sm font-medium text-slate-700 mb-3">
                Интенсивность боли:
              </p>
              <PainScale
                value={(currentAnswer.intensity as number) ?? 5}
                onChange={(value) =>
                  setCurrentAnswer((prev) => ({ ...prev, intensity: value }))
                }
                min={currentNode.min_value}
                max={currentNode.max_value}
              />
            </div>
          </div>
        )

      case 'scale_1_10':
      case 'slider':
        return (
          <PainScale
            value={(currentAnswer.value as number) ?? currentNode.min_value ?? 1}
            onChange={(value) => setCurrentAnswer({ value })}
            min={currentNode.min_value ?? 1}
            max={currentNode.max_value ?? 10}
          />
        )

      case 'text_input':
        return (
          <TextInput
            value={(currentAnswer.text as string) || ''}
            onChange={(text) => setCurrentAnswer({ text })}
            placeholder={currentNode.placeholder}
            multiline={true}
          />
        )

      case 'number_input':
        return (
          <NumberInput
            value={(currentAnswer.value as number) ?? null}
            onChange={(value) => setCurrentAnswer({ value: value ?? undefined })}
            placeholder={currentNode.placeholder}
            min={currentNode.min_value}
            max={currentNode.max_value}
          />
        )

      case 'consent_screen':
        return (
          <div className="space-y-4">
            <label className="flex items-start gap-3 p-4 bg-white border-2 border-slate-200 rounded-xl cursor-pointer hover:border-primary-400 transition-colors">
              <input
                type="checkbox"
                checked={currentAnswer.selected === true}
                onChange={(e) =>
                  setCurrentAnswer((prev) => ({ ...prev, selected: e.target.checked }))
                }
                className="mt-0.5 w-5 h-5 text-primary-600 rounded focus:ring-primary-500"
              />
              <span className="text-slate-700 font-medium">
                Я даю согласие на обработку персональных данных
              </span>
            </label>
          </div>
        )

      default:
        return (
          <p className="text-slate-500">
            Неизвестный тип вопроса: {currentNode.type}
          </p>
        )
    }
  }

  // Варианты анимации
  const variants = {
    enter: (direction: 'forward' | 'backward') => ({
      x: direction === 'forward' ? 50 : -50,
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
    },
    exit: (direction: 'forward' | 'backward') => ({
      x: direction === 'forward' ? -50 : 50,
      opacity: 0,
    }),
  }

  if (!currentNode) {
    // Если идёт восстановление сессии — показываем экран загрузки
    if (isRestoring) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-primary-600 animate-spin mx-auto" />
            <p className="mt-4 text-slate-600">Восстановление опроса...</p>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Header onClose={handleClose} />
      {expiresAt && <SessionTimer expiresAt={expiresAt} onExpire={handleSessionExpired} />}
      <ProgressBar progress={progress} />
      
      <PageContainer>
        <AnimatePresence mode="wait" custom={animationDirection}>
          <motion.div
            key={currentNodeId}
            custom={animationDirection}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="space-y-6"
          >
            {/* Заголовок вопроса */}
            {currentNode.type !== 'info_screen' && (
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {currentNode.question_text}
                </h2>
                {currentNode.description && (
                  <p className="mt-2 text-slate-500">{currentNode.description}</p>
                )}
              </div>
            )}

            {/* Контент */}
            {renderContent()}
          </motion.div>
        </AnimatePresence>
      </PageContainer>

      <Footer
        onBack={canGoBack() ? handleBack : undefined}
        onNext={handleNext}
        nextDisabled={!canProceed()}
        showBack={canGoBack()}
        isLoading={isLoading}
        nextLabel={currentNode.is_final ? 'Завершить' : 'Далее'}
      />
    </div>
  )
}

export default SurveyPage
