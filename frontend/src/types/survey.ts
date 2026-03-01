/**
 * Типы данных для опросника
 */

// Вариант ответа
export interface SurveyOption {
  id: string
  text: string
  value: string
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
    | 'single_choice'
    | 'multi_choice'
    | 'multi_choice_with_input'
    | 'scale_1_10'
    | 'slider'
    | 'body_map'
    | 'text_input'
    | 'number_input'
    | 'consent_screen'
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
  // Значение варианта-исключения (сбрасывает все остальные при выборе)
  exclusive_option?: string
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
  selected?: string | string[] | boolean
  value?: number
  text?: string
  locations?: string[]
  intensity?: number
  [key: string]: unknown
}

// Ответы API
export interface TokenValidationResponse {
  valid: boolean
  session_id?: string
  patient_name?: string
  message?: string
  expires_at?: string
  resolved_token?: string  // JWT при использовании короткого кода
}

export interface SurveyStartResponse {
  session_id: string
  patient_name?: string
  survey_config: SurveyConfig
  message: string
  expires_at?: string // ISO timestamp когда сессия истечёт
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
