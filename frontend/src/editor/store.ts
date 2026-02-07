// ============================================
// Zustand Store для редактора опросника
// ============================================

import { create } from 'zustand';
import { 
  FlowNode, 
  FlowEdge, 
  SurveyStructure, 
  SurveyNodeData, 
  ValidationResult,
  HistoryEntry,
  NodeType,
  NODE_TYPE_CONFIG,
} from './types';

// API базовый URL
const API_BASE = `${import.meta.env.VITE_API_URL || '/api/v1'}/editor`;

// Максимальный размер истории
const MAX_HISTORY_SIZE = 50;

// Интервал автосохранения (3 минуты)
const AUTOSAVE_INTERVAL = 3 * 60 * 1000;

/**
 * Helper функция для API запросов с поддержкой Basic Auth
 */
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  // Проверяем, есть ли сохранённые учётные данные
  const authData = sessionStorage.getItem('admin_auth');
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };
  
  if (authData) {
    const { username, password } = JSON.parse(authData);
    const credentials = btoa(`${username}:${password}`);
    headers['Authorization'] = `Basic ${credentials}`;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Для поддержки сессионных cookie
  });
  
  // Если 401 и нет учётных данных, запрашиваем их
  if (response.status === 401 && !authData) {
    const username = prompt('Введите имя пользователя администратора:');
    const password = prompt('Введите пароль:');
    
    if (username && password) {
      sessionStorage.setItem('admin_auth', JSON.stringify({ username, password }));
      return fetchWithAuth(url, options); // Повторяем запрос
    }
    
    throw new Error('Требуется аутентификация');
  }
  
  return response;
}

interface EditorStore {
  // Состояние
  survey: SurveyStructure | null;
  nodes: FlowNode[];
  edges: FlowEdge[];
  selectedNodeId: string | null;
  isDirty: boolean;
  lastSaved: Date | null;
  isSaving: boolean;
  isLoading: boolean;
  error: string | null;
  
  // История
  history: HistoryEntry[];
  historyIndex: number;
  
  // Валидация
  validationResult: ValidationResult | null;
  
  // Автосохранение
  autosaveTimer: ReturnType<typeof setInterval> | null;
  
  // Действия
  loadSurvey: (surveyId: number) => Promise<void>;
  saveSurvey: () => Promise<void>;
  createSurvey: (name: string, description?: string) => Promise<number>;
  
  // Управление узлами
  setNodes: (nodes: FlowNode[]) => void;
  setEdges: (edges: FlowEdge[]) => void;
  addNode: (type: NodeType, position: { x: number; y: number }) => void;
  updateNode: (nodeId: string, data: Partial<SurveyNodeData>) => void;
  deleteNode: (nodeId: string) => void;
  duplicateNode: (nodeId: string) => void;
  
  // Управление связями
  addEdge: (sourceId: string, targetId: string, condition?: string) => void;
  deleteEdge: (edgeId: string) => void;
  updateEdge: (edgeId: string, data: { condition?: string }) => void;
  
  // Выбор узла
  selectNode: (nodeId: string | null) => void;
  
  // История
  pushHistory: (action: string) => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  
  // Валидация
  validate: () => Promise<ValidationResult>;
  
  // Импорт/Экспорт
  exportJSON: () => string;
  importJSON: (json: string) => Promise<void>;
  
  // Автосохранение
  startAutosave: () => void;
  stopAutosave: () => void;
  
  // Сброс
  reset: () => void;
  
  // Вспомогательные
  setStartNode: (nodeId: string) => void;
  updateSurveyMeta: (meta: { name?: string; description?: string }) => void;
}

// Генерация уникального ID
const generateId = () => `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Конвертация узлов опросника в React Flow формат
const surveyNodesToFlowNodes = (nodes: SurveyNodeData[], startNode: string): FlowNode[] => {
  return nodes.map((node, index) => ({
    id: node.id,
    type: 'surveyNode',
    position: node.position || { x: 100 + (index % 3) * 350, y: 100 + Math.floor(index / 3) * 200 },
    data: {
      ...node,
      label: node.question_text,
      isStart: node.id === startNode,
    },
  }));
};

// Конвертация логики в рёбра React Flow
const surveyLogicToEdges = (nodes: SurveyNodeData[]): FlowEdge[] => {
  const edges: FlowEdge[] = [];
  
  nodes.forEach(node => {
    if (node.logic) {
      node.logic.forEach((rule, index) => {
        edges.push({
          id: `${node.id}-${rule.next_node}-${index}`,
          source: node.id,
          target: rule.next_node,
          type: 'smoothstep',
          animated: rule.default,
          label: rule.condition || (rule.default ? 'По умолчанию' : ''),
          data: {
            condition: rule.condition,
            isDefault: rule.default,
          },
        });
      });
    }
  });
  
  return edges;
};

// Конвертация React Flow в структуру опросника
const flowToSurveyStructure = (
  nodes: FlowNode[], 
  edges: FlowEdge[], 
  survey: SurveyStructure
): SurveyStructure => {
  const startNode = nodes.find(n => n.data.isStart)?.id || nodes[0]?.id || '';
  
  const surveyNodes: SurveyNodeData[] = nodes.map(node => {
    // Собираем логику из рёбер
    const nodeEdges = edges.filter(e => e.source === node.id);
    const logic = nodeEdges.map(edge => ({
      condition: edge.data?.condition,
      next_node: edge.target,
      default: edge.data?.isDefault || false,
    }));
    
    return {
      id: node.id,
      type: node.data.type,
      question_text: node.data.question_text,
      description: node.data.description,
      required: node.data.required ?? true,
      options: node.data.options,
      logic: logic.length > 0 ? logic : undefined,
      additional_fields: node.data.additional_fields,
      min_value: node.data.min_value,
      max_value: node.data.max_value,
      step: node.data.step,
      placeholder: node.data.placeholder,
      max_length: node.data.max_length,
      is_final: node.data.is_final,
      position: node.position,
    };
  });
  
  return {
    ...survey,
    start_node: startNode,
    nodes: surveyNodes,
  };
};

export const useEditorStore = create<EditorStore>((set, get) => ({
  // Начальное состояние
  survey: null,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  isDirty: false,
  lastSaved: null,
  isSaving: false,
  isLoading: false,
  error: null,
  history: [],
  historyIndex: -1,
  validationResult: null,
  autosaveTimer: null,
  
  // Загрузка опросника
  loadSurvey: async (surveyId: number) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await fetchWithAuth(`${API_BASE}/surveys/${surveyId}`);
      if (!response.ok) {
        throw new Error('Не удалось загрузить опросник');
      }
      
      const survey: SurveyStructure = await response.json();
      const nodes = surveyNodesToFlowNodes(survey.nodes, survey.start_node);
      const edges = surveyLogicToEdges(survey.nodes);
      
      set({
        survey,
        nodes,
        edges,
        isLoading: false,
        isDirty: false,
        history: [],
        historyIndex: -1,
        validationResult: null,
      });
      
      // Начинаем автосохранение
      get().startAutosave();
      
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка загрузки',
        isLoading: false 
      });
    }
  },
  
  // Сохранение опросника
  saveSurvey: async () => {
    const { survey, nodes, edges, isDirty } = get();
    
    if (!survey || !isDirty) return;
    
    set({ isSaving: true, error: null });
    
    try {
      const updatedSurvey = flowToSurveyStructure(nodes, edges, survey);
      
      const response = await fetchWithAuth(`${API_BASE}/surveys/${survey.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedSurvey),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail?.message || 'Ошибка сохранения');
      }
      
      set({
        isSaving: false,
        isDirty: false,
        lastSaved: new Date(),
      });
      
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка сохранения',
        isSaving: false 
      });
    }
  },
  
  // Создание нового опросника
  createSurvey: async (name: string, description?: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const newSurvey: SurveyStructure = {
        name,
        description,
        version: '1.0',
        start_node: 'start',
        nodes: [{
          id: 'start',
          type: 'single_choice',
          question_text: 'Первый вопрос',
          required: true,
          options: [
            { id: 'opt1', text: 'Вариант 1', value: 'opt1' },
            { id: 'opt2', text: 'Вариант 2', value: 'opt2' },
          ],
          position: { x: 250, y: 100 },
        }],
      };
      
      const response = await fetchWithAuth(`${API_BASE}/surveys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSurvey),
      });
      
      if (!response.ok) {
        throw new Error('Не удалось создать опросник');
      }
      
      const created: SurveyStructure = await response.json();
      
      set({ isLoading: false });
      
      return created.id!;
      
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка создания',
        isLoading: false 
      });
      throw error;
    }
  },
  
  // Установка узлов
  setNodes: (nodes: FlowNode[]) => {
    get().pushHistory('Изменение узлов');
    set({ nodes, isDirty: true });
  },
  
  // Установка связей
  setEdges: (edges: FlowEdge[]) => {
    get().pushHistory('Изменение связей');
    set({ edges, isDirty: true });
  },
  
  // Добавление узла
  addNode: (type: NodeType, position: { x: number; y: number }) => {
    const config = NODE_TYPE_CONFIG[type];
    const id = generateId();
    
    const newNode: FlowNode = {
      id,
      type: 'surveyNode',
      position,
      data: {
        id,
        type,
        question_text: `Новый вопрос (${config.name})`,
        required: true,
        label: `Новый вопрос (${config.name})`,
        options: config.has_options ? [
          { id: 'opt1', text: 'Вариант 1', value: 'opt1' },
        ] : undefined,
        min_value: config.has_min_max ? 1 : undefined,
        max_value: config.has_min_max ? 10 : undefined,
        is_final: type === 'info_screen' ? true : undefined,
      },
    };
    
    get().pushHistory('Добавление узла');
    set(state => ({
      nodes: [...state.nodes, newNode],
      isDirty: true,
      selectedNodeId: id,
    }));
  },
  
  // Обновление узла
  updateNode: (nodeId: string, data: Partial<SurveyNodeData>) => {
    get().pushHistory('Обновление узла');
    set(state => ({
      nodes: state.nodes.map(node =>
        node.id === nodeId
          ? { 
              ...node, 
              data: { 
                ...node.data, 
                ...data,
                label: data.question_text || node.data.label,
              } 
            }
          : node
      ),
      isDirty: true,
    }));
  },
  
  // Удаление узла
  deleteNode: (nodeId: string) => {
    get().pushHistory('Удаление узла');
    set(state => ({
      nodes: state.nodes.filter(n => n.id !== nodeId),
      edges: state.edges.filter(e => e.source !== nodeId && e.target !== nodeId),
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
      isDirty: true,
    }));
  },
  
  // Дублирование узла
  duplicateNode: (nodeId: string) => {
    const { nodes } = get();
    const node = nodes.find(n => n.id === nodeId);
    
    if (!node) return;
    
    const newId = generateId();
    const newNode: FlowNode = {
      ...node,
      id: newId,
      position: {
        x: node.position.x + 50,
        y: node.position.y + 50,
      },
      data: {
        ...node.data,
        id: newId,
        question_text: `${node.data.question_text} (копия)`,
        label: `${node.data.label} (копия)`,
        isStart: false,
      },
    };
    
    get().pushHistory('Дублирование узла');
    set(state => ({
      nodes: [...state.nodes, newNode],
      isDirty: true,
      selectedNodeId: newId,
    }));
  },
  
  // Добавление связи
  addEdge: (sourceId: string, targetId: string, condition?: string) => {
    const edgeId = `${sourceId}-${targetId}-${Date.now()}`;
    
    const newEdge: FlowEdge = {
      id: edgeId,
      source: sourceId,
      target: targetId,
      type: 'smoothstep',
      label: condition || '',
      data: {
        condition,
        isDefault: !condition,
      },
    };
    
    get().pushHistory('Добавление связи');
    set(state => ({
      edges: [...state.edges, newEdge],
      isDirty: true,
    }));
  },
  
  // Удаление связи
  deleteEdge: (edgeId: string) => {
    get().pushHistory('Удаление связи');
    set(state => ({
      edges: state.edges.filter(e => e.id !== edgeId),
      isDirty: true,
    }));
  },
  
  // Обновление связи
  updateEdge: (edgeId: string, data: { condition?: string }) => {
    get().pushHistory('Обновление связи');
    set(state => ({
      edges: state.edges.map(edge =>
        edge.id === edgeId
          ? { 
              ...edge, 
              label: data.condition || 'По умолчанию',
              data: { 
                ...edge.data, 
                condition: data.condition,
                isDefault: !data.condition,
              } 
            }
          : edge
      ),
      isDirty: true,
    }));
  },
  
  // Выбор узла
  selectNode: (nodeId: string | null) => {
    set({ selectedNodeId: nodeId });
  },
  
  // Добавление в историю
  pushHistory: (action: string) => {
    const { nodes, edges, history, historyIndex } = get();
    
    // Обрезаем историю после текущего индекса (отменяем "redo" стек)
    const newHistory = history.slice(0, historyIndex + 1);
    
    // Добавляем новую запись
    newHistory.push({
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
      timestamp: new Date(),
      action,
    });
    
    // Ограничиваем размер истории
    if (newHistory.length > MAX_HISTORY_SIZE) {
      newHistory.shift();
    }
    
    set({
      history: newHistory,
      historyIndex: newHistory.length - 1,
    });
  },
  
  // Отмена
  undo: () => {
    const { history, historyIndex } = get();
    
    if (historyIndex <= 0) return;
    
    const prevState = history[historyIndex - 1];
    
    set({
      nodes: JSON.parse(JSON.stringify(prevState.nodes)),
      edges: JSON.parse(JSON.stringify(prevState.edges)),
      historyIndex: historyIndex - 1,
      isDirty: true,
    });
  },
  
  // Повтор
  redo: () => {
    const { history, historyIndex } = get();
    
    if (historyIndex >= history.length - 1) return;
    
    const nextState = history[historyIndex + 1];
    
    set({
      nodes: JSON.parse(JSON.stringify(nextState.nodes)),
      edges: JSON.parse(JSON.stringify(nextState.edges)),
      historyIndex: historyIndex + 1,
      isDirty: true,
    });
  },
  
  // Можно ли отменить
  canUndo: () => {
    const { historyIndex } = get();
    return historyIndex > 0;
  },
  
  // Можно ли повторить
  canRedo: () => {
    const { history, historyIndex } = get();
    return historyIndex < history.length - 1;
  },
  
  // Валидация
  validate: async () => {
    const { survey, nodes, edges } = get();
    
    if (!survey) {
      return { valid: false, errors: [{ type: 'error', message: 'Опросник не загружен' }], warnings: [] };
    }
    
    try {
      const structure = flowToSurveyStructure(nodes, edges, survey);
      
      const response = await fetchWithAuth(`${API_BASE}/validate-structure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(structure),
      });
      
      const result: ValidationResult = await response.json();
      
      set({ validationResult: result });
      
      return result;
      
    } catch (error) {
      const result: ValidationResult = {
        valid: false,
        errors: [{ type: 'error', message: 'Ошибка валидации' }],
        warnings: [],
      };
      set({ validationResult: result });
      return result;
    }
  },
  
  // Экспорт в JSON
  exportJSON: () => {
    const { survey, nodes, edges } = get();
    
    if (!survey) return '';
    
    const structure = flowToSurveyStructure(nodes, edges, survey);
    
    return JSON.stringify({
      name: structure.name,
      description: structure.description,
      version: structure.version,
      exported_at: new Date().toISOString(),
      config: structure,
    }, null, 2);
  },
  
  // Импорт из JSON
  importJSON: async (json: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const data = JSON.parse(json);
      
      const response = await fetchWithAuth(`${API_BASE}/surveys/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail?.message || 'Ошибка импорта');
      }
      
      const imported: SurveyStructure = await response.json();
      
      // Загружаем импортированный опросник
      await get().loadSurvey(imported.id!);
      
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка импорта',
        isLoading: false 
      });
    }
  },
  
  // Запуск автосохранения
  startAutosave: () => {
    const { autosaveTimer } = get();
    
    // Останавливаем предыдущий таймер
    if (autosaveTimer) {
      clearInterval(autosaveTimer);
    }
    
    const timer = setInterval(() => {
      const { isDirty } = get();
      if (isDirty) {
        get().saveSurvey();
      }
    }, AUTOSAVE_INTERVAL);
    
    set({ autosaveTimer: timer });
  },
  
  // Остановка автосохранения
  stopAutosave: () => {
    const { autosaveTimer } = get();
    
    if (autosaveTimer) {
      clearInterval(autosaveTimer);
      set({ autosaveTimer: null });
    }
  },
  
  // Сброс
  reset: () => {
    get().stopAutosave();
    
    set({
      survey: null,
      nodes: [],
      edges: [],
      selectedNodeId: null,
      isDirty: false,
      lastSaved: null,
      isSaving: false,
      isLoading: false,
      error: null,
      history: [],
      historyIndex: -1,
      validationResult: null,
    });
  },
  
  // Установка стартового узла
  setStartNode: (nodeId: string) => {
    get().pushHistory('Изменение стартового узла');
    set(state => ({
      nodes: state.nodes.map(node => ({
        ...node,
        data: {
          ...node.data,
          isStart: node.id === nodeId,
        },
      })),
      isDirty: true,
    }));
  },
  
  // Обновление метаданных опросника
  updateSurveyMeta: (meta: { name?: string; description?: string }) => {
    set(state => ({
      survey: state.survey ? { ...state.survey, ...meta } : null,
      isDirty: true,
    }));
  },
}));
