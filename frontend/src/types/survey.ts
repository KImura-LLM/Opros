/**
 * Типы данных для опросника
 */

// Вариант ответа
export interface SurveyOption {
  id: string
  text: string
  value: string
  icon?: string
}

// Дополнительное поле ввода
export interface AdditionalField {
  id: string
  type: 'text' | 'number' | 'single_choice'
  label: string
  placeholder?: string
  min?: number
  max?: number
  options?: SurveyOption[]
  show_if?: string
}

// Правило перехода
export interface NodeLogic {
  condition?: string
  next_node: string
  default?: boolean
}

// Узел (вопрос) опросника
export interface SurveyNode {
  id: string
  type:
    | 'info_screen'
    | 'consent_screen'
    | 'single_choice'
    | 'multi_choice'
    | 'multi_choice_with_input'
    | 'scale_1_10'
    | 'body_map'
    | 'text_input'
    | 'number_input'
  question_text: string
  description?: string
  options?: SurveyOption[]
  additional_fields?: AdditionalField[]
  logic?: NodeLogic[]
  required: boolean
  min_value?: number
  max_value?: number
  placeholder?: string
  is_final?: boolean
}

// Конфигурация опросника
export interface SurveyConfig {
  id: number
  name: string
  version: string
  description?: string
  start_node: string
  branch_mapping?: Record<string, string>
  nodes: SurveyNode[]
}

// Ответ пользователя (общий тип)
export interface AnswerData {
  selected?: string | string[]
  value?: number
  text?: string
  locations?: string[]
  intensity?: number
  [key: string]: unknown
}

// Прогресс опроса
export interface SurveyProgress {
  current_node: string
  answers: Record<string, AnswerData>
  history: string[]
  started_at?: string
}

// Ответы API
export interface TokenValidationResponse {
  valid: boolean
  session_id?: string
  patient_name?: string
  message?: string
}

export interface SurveyStartResponse {
  session_id: string
  patient_name?: string
  survey_config: SurveyConfig
  message: string
}

export interface SurveyAnswerResponse {
  success: boolean
  next_node?: string
  progress: number
}

export interface SurveyCompleteResponse {
  success: boolean
  message: string
  report_sent: boolean
}

// Направление анимации
export type AnimationDirection = 'forward' | 'backward'
