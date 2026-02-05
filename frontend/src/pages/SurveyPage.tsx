/**
 * Страница прохождения опроса
 */

import React, { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useSurveyStore } from '@/store'
import { submitAnswer, completeSurvey } from '@/api'
import { Header, ProgressBar, Footer, PageContainer } from '@/components/layout'
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
    setCurrentNode,
    setAnswer,
    setProgress,
    goBack,
    canGoBack,
  } = useSurveyStore()

  const [currentAnswer, setCurrentAnswer] = useState<AnswerData>({})
  const [isLoading, setIsLoading] = useState(false)

  // Получение текущего узла
  const currentNode: SurveyNode | null = config?.nodes.find(
    (n) => n.id === currentNodeId
  ) || null

  // Загрузка сохранённого ответа при смене узла
  useEffect(() => {
    const savedAnswer = answers[currentNodeId]
    if (savedAnswer) {
      setCurrentAnswer(savedAnswer)
    } else {
      setCurrentAnswer({})
    }
  }, [currentNodeId, answers])

  // Редирект если нет данных
  useEffect(() => {
    if (!config || !sessionId) {
      navigate('/')
    }
  }, [config, sessionId, navigate])

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
      const locations = currentAnswer.locations as string[] | undefined
      const intensity = currentAnswer.intensity
      return Array.isArray(locations) && locations.length > 0 && intensity !== undefined
    }
    
    // Scale 1-10
    if (currentNode.type === 'scale_1_10') {
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
    
    setIsLoading(true)
    
    try {
      // Сохраняем ответ локально
      if (currentNode.type !== 'info_screen') {
        setAnswer(currentNodeId, currentAnswer)
      }
      
      // Отправляем на сервер
      if (currentNode.type !== 'info_screen' && sessionId) {
        const response = await submitAnswer(sessionId, currentNodeId, currentAnswer)
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
      } else if (currentNode.is_final) {
        // Завершение опроса
        await completeSurvey(sessionId)
        navigate('/complete')
      }
    } catch (error) {
      console.error('Error submitting answer:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Обработка нажатия "Назад"
  const handleBack = () => {
    goBack()
  }

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
          <SingleChoice
            options={currentNode.options || []}
            value={(currentAnswer.selected as string) || null}
            onChange={(value) => setCurrentAnswer({ selected: value })}
          />
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
            />
            
            {/* Дополнительные поля */}
            {currentNode.additional_fields?.map((field) => {
              if (field.type === 'number') {
                return (
                  <NumberInput
                    key={field.id}
                    label={field.label}
                    placeholder={field.placeholder}
                    value={(currentAnswer[field.id] as number) || null}
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
                value={(currentAnswer.intensity as number) || 5}
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
        return (
          <PainScale
            value={(currentAnswer.value as number) || 5}
            onChange={(value) => setCurrentAnswer({ value })}
            min={currentNode.min_value || 1}
            max={currentNode.max_value || 10}
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
            value={(currentAnswer.value as number) || null}
            onChange={(value) => setCurrentAnswer({ value })}
            placeholder={currentNode.placeholder}
            min={currentNode.min_value}
            max={currentNode.max_value}
          />
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
    return null
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Header onClose={handleClose} />
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
