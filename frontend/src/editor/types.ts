// ============================================
// Типы для визуального редактора опросника
// ============================================

// Примечание: типы Node и Edge из @xyflow/react расширяем через дженерики

// Типы узлов опросника
export type NodeType = 
  | 'single_choice'
  | 'multi_choice'
  | 'multi_choice_with_input'
  | 'text_input'
  | 'slider'
  | 'body_map'
  | 'info_screen'
  | 'consent_screen';

// Позиция узла на canvas
export interface NodePosition {
  x: number;
  y: number;
}

// Вариант ответа
export interface NodeOption {
  id: string;
  text: string;
  value?: string;
}

// Правило перехода
export interface NodeLogic {
  condition?: string;
  next_node: string;
  default?: boolean;
}

// Дополнительное поле
export interface AdditionalField {
  id: string;
  type: string;
  label: string;
  placeholder?: string;
  min?: number;
  max?: number;
  options?: { id: string; text: string }[];
  show_if?: string;
}

// Данные узла опросника
export interface SurveyNodeData {
  id: string;
  type: NodeType;
  question_text: string;
  description?: string;
  required: boolean;
  options?: NodeOption[];
  logic?: NodeLogic[];
  additional_fields?: AdditionalField[];
  
  // Для slider/scale
  min_value?: number;
  max_value?: number;
  step?: number;
  
  // Для text_input
  placeholder?: string;
  max_length?: number;
  
  // Для info_screen
  is_final?: boolean;
  
  // Значение варианта-исключения для multi_choice (сбрасывает все остальные при выборе)
  exclusive_option?: string;
  
  // Позиция на canvas
  position?: NodePosition;
}

// Данные узла для React Flow
export interface FlowNodeData extends SurveyNodeData {
  label: string;
  isStart?: boolean;
  // Index signature для совместимости с React Flow
  [key: string]: unknown;
}

// Узел React Flow (используем базовый тип)
export interface FlowNode {
  id: string;
  type?: string;
  position: { x: number; y: number };
  data: FlowNodeData;
  selected?: boolean;
  dragging?: boolean;
}

// Ребро React Flow
export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
  label?: string;
  data?: {
    condition?: string;
    isDefault?: boolean;
  };
}

// Структура опросника
export interface SurveyStructure {
  id?: number;
  name: string;
  version: string;
  description?: string;
  start_node: string;
  branch_mapping?: Record<string, string>;
  nodes: SurveyNodeData[];
}

// Элемент списка опросников
export interface SurveyListItem {
  id: number;
  name: string;
  version: string;
  description?: string;
  is_active: boolean;
  nodes_count: number;
  created_at: string;
  updated_at?: string;
}

// Ошибка валидации
export interface ValidationError {
  type: 'error' | 'warning';
  node_id?: string;
  message: string;
}

// Результат валидации
export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

// Тип узла (для палитры)
export interface NodeTypeInfo {
  id: NodeType;
  name: string;
  description: string;
  icon: string;
  color: string;
  has_options: boolean;
  has_logic: boolean;
  has_min_max?: boolean;
  has_additional_fields?: boolean;
  can_be_final?: boolean;
}

// Состояние редактора
export interface EditorState {
  survey: SurveyStructure | null;
  nodes: FlowNode[];
  edges: FlowEdge[];
  selectedNode: string | null;
  isDirty: boolean;
  lastSaved: Date | null;
  
  // История для Undo/Redo
  history: HistoryEntry[];
  historyIndex: number;
  
  // Валидация
  validationResult: ValidationResult | null;
}

// Запись истории
export interface HistoryEntry {
  nodes: FlowNode[];
  edges: FlowEdge[];
  timestamp: Date;
  action: string;
}

// Настройки узлов по типу
export const NODE_TYPE_CONFIG: Record<NodeType, NodeTypeInfo> = {
  single_choice: {
    id: 'single_choice',
    name: 'Один выбор',
    description: 'Пользователь выбирает один вариант',
    icon: 'CircleDot',
    color: '#3b82f6',
    has_options: true,
    has_logic: true,
  },
  multi_choice: {
    id: 'multi_choice',
    name: 'Множественный выбор',
    description: 'Можно выбрать несколько вариантов',
    icon: 'CheckSquare',
    color: '#8b5cf6',
    has_options: true,
    has_logic: true,
  },
  multi_choice_with_input: {
    id: 'multi_choice_with_input',
    name: 'Выбор + ввод',
    description: 'Множественный выбор с доп. полями',
    icon: 'ListPlus',
    color: '#a855f7',
    has_options: true,
    has_logic: true,
    has_additional_fields: true,
  },
  text_input: {
    id: 'text_input',
    name: 'Текстовый ответ',
    description: 'Свободный ввод текста',
    icon: 'Type',
    color: '#10b981',
    has_options: false,
    has_logic: true,
  },
  slider: {
    id: 'slider',
    name: 'Слайдер',
    description: 'Выбор значения на шкале',
    icon: 'SlidersHorizontal',
    color: '#f59e0b',
    has_options: false,
    has_logic: true,
    has_min_max: true,
  },
  body_map: {
    id: 'body_map',
    name: 'Карта тела',
    description: 'Выбор зоны на карте тела',
    icon: 'User',
    color: '#ef4444',
    has_options: true,
    has_logic: true,
    has_min_max: true,
  },
  info_screen: {
    id: 'info_screen',
    name: 'Информационный экран',
    description: 'Текст без ввода (финиш)',
    icon: 'Info',
    color: '#6b7280',
    has_options: false,
    has_logic: false,
    can_be_final: true,
  },
  consent_screen: {
    id: 'consent_screen',
    name: 'Согласие (152-ФЗ)',
    description: 'Согласие на обработку персональных данных',
    icon: 'ShieldCheck',
    color: '#059669',
    has_options: false,
    has_logic: true,
    can_be_final: false,
  },
};
