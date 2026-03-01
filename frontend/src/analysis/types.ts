// ============================================
// Типы для редактора системного анализа
// ============================================

/**
 * Триггер — конкретный вариант ответа на вопрос,
 * при выборе которого срабатывает правило.
 *
 * Для вопросов с вариантами (single_choice, multi_choice и т.д.):
 *   match_mode = 'exact' (по умолчанию), option_value = id варианта.
 *
 * Для текстовых вопросов (text_input) и свободных полей:
 *   match_mode = 'contains', option_value = подстрока для поиска.
 */
export interface AnalysisTrigger {
  node_id: string;
  option_value: string;
  /** Режим сравнения:
   *  'exact'    — точное совпадение / вхождение в список (по умолчанию),
   *  'contains' — подстрока (регистронезависимо),
   *  'gte'      — числовое значение ≥ порога (слайдер / шкала) */
  match_mode?: 'exact' | 'contains' | 'gte';
}

/**
 * Правило системного анализа.
 * Содержит набор триггеров и текст сообщения для врача.
 */
/**
 * Допустимые цвета для правила (цветовая индикация в отчёте).
 */
export type RuleColor = 'red' | 'orange' | 'yellow' | 'green';

export interface AnalysisRule {
  id: string;
  name: string;
  triggers: AnalysisTrigger[];
  trigger_mode: 'any' | 'all';
  message: string;
  /** Цвет фона триггера в отчёте */
  color?: RuleColor;
}

/**
 * Полная структура правил для одного опросника.
 */
export interface AnalysisRulesPayload {
  rules: AnalysisRule[];
}

/**
 * Вариант ответа вопроса (для отображения в дереве).
 */
export interface QuestionOption {
  id: string;
  text: string;
  value: string;
}

/**
 * Упрощённое представление вопроса (узла) для дерева.
 */
export interface QuestionItem {
  id: string;
  type: string;
  question_text: string;
  options: QuestionOption[];
  /** true если вопрос принимает свободный текстовый ввод
   *  (text_input или имеет additional_fields с type=text) */
  hasTextInput: boolean;
  /** Минимальное значение (для slider / scale) */
  minValue?: number;
  /** Максимальное значение (для slider / scale) */
  maxValue?: number;
}

/**
 * Правило перехода в графе опросника.
 */
export interface NodeLogic {
  condition?: string;
  next_node: string;
  default?: boolean;
}

/**
 * Сырой узел опросника, как он приходит с API.
 */
export interface RawSurveyNode {
  id: string;
  type: string;
  question_text: string;
  options?: { id: string; text: string; value?: string }[];
  logic?: NodeLogic[];
  additional_fields?: { id: string; type: string; label: string }[];
  is_final?: boolean;
  min_value?: number;
  max_value?: number;
  placeholder?: string;
}

/**
 * Структура опросника (минимально необходимая для редактора анализа).
 */
export interface SurveyStructureMinimal {
  id: number;
  name: string;
  version: string;
  start_node: string;
  nodes: RawSurveyNode[];
}
