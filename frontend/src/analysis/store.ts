// ============================================
// Zustand Store для редактора системного анализа
// ============================================

import { create } from 'zustand';
import type {
  AnalysisRule,
  AnalysisTrigger,
  SurveyStructureMinimal,
  RawSurveyNode,
  QuestionItem,
} from './types';

// API базовый URL
const API_BASE = `${import.meta.env.VITE_API_URL || '/api/v1'}/editor`;

/**
 * Генерация уникального ID для правила
 */
function generateRuleId(): string {
  return `rule_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Helper — запрос с cookie-аутентификацией (общий с editor/store.ts).
 */
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    },
    credentials: 'include',
  });

  if (response.status === 401) {
    window.location.href = '/admin/login';
    throw new Error('Требуется аутентификация');
  }

  return response;
}

// ──────────────────────────────────────────────
// Обход графа опросника (порядок по самому длинному пути)
// ──────────────────────────────────────────────

/**
 * Обходит граф узлов опросника от start_node.
 * Использует DFS и при ветвлении (несколько next_node) сначала идёт
 * по самой длинной ветке, чтобы все узлы попали в результат.
 *
 * Возвращает массив id узлов в порядке обхода.
 */
function traverseGraphLongestPath(
  nodesMap: Map<string, RawSurveyNode>,
  startNode: string,
): string[] {
  // 1. Для каждого узла вычисляем максимальную глубину (мемоизация)
  const depthCache = new Map<string, number>();

  function maxDepth(nodeId: string, visited: Set<string>): number {
    if (depthCache.has(nodeId)) return depthCache.get(nodeId)!;
    if (visited.has(nodeId)) return 0; // цикл
    const node = nodesMap.get(nodeId);
    if (!node) return 0;

    visited.add(nodeId);
    let best = 0;
    const nextIds = getNextNodeIds(node);
    for (const nid of nextIds) {
      best = Math.max(best, 1 + maxDepth(nid, visited));
    }
    visited.delete(nodeId);
    depthCache.set(nodeId, best);
    return best;
  }

  // Предварительно вычисляем глубины
  for (const id of nodesMap.keys()) {
    maxDepth(id, new Set());
  }

  // 2. DFS: на каждом шаге сортируем потомков по убыванию глубины
  //    (сначала идём по самой длинной ветке → все узлы попадут в результат)
  const result: string[] = [];
  const globalVisited = new Set<string>();

  function dfs(nodeId: string) {
    if (globalVisited.has(nodeId)) return;
    const node = nodesMap.get(nodeId);
    if (!node) return;

    globalVisited.add(nodeId);
    result.push(nodeId);

    const nextIds = getNextNodeIds(node);
    // Сортируем: сначала ветка с наибольшей глубиной
    const sorted = [...nextIds].sort(
      (a, b) => (depthCache.get(b) ?? 0) - (depthCache.get(a) ?? 0),
    );
    for (const nid of sorted) {
      dfs(nid);
    }
  }

  dfs(startNode);

  // 3. Добавляем узлы, недоступные из start_node (на всякий случай)
  for (const id of nodesMap.keys()) {
    if (!globalVisited.has(id)) {
      result.push(id);
    }
  }

  return result;
}

/** Извлекает все возможные next_node из logic-правил узла. */
function getNextNodeIds(node: RawSurveyNode): string[] {
  if (!node.logic) return [];
  const ids: string[] = [];
  for (const rule of node.logic) {
    if (rule.next_node && !ids.includes(rule.next_node)) {
      ids.push(rule.next_node);
    }
  }
  return ids;
}

// ──────────────────────────────────────────────
// Типы, которые НЕ показываем в редакторе анализа
// (info_screen без вариантов / consent; welcome и т.д.)
// ──────────────────────────────────────────────
const SKIP_TYPES = new Set(['info_screen']);

/**
 * Конвертирует сырой узел в QuestionItem для UI.
 * Возвращает null если узел не подлежит показу.
 */
function rawNodeToQuestionItem(node: RawSurveyNode): QuestionItem | null {
  // Пропускаем финальные экраны и info_screen
  if (SKIP_TYPES.has(node.type)) return null;

  const options = (node.options || []).map((o) => ({
    id: o.id,
    text: o.text,
    value: o.value || o.id,
  }));

  // Определяем, является ли вопрос текстовым
  const isTextType = node.type === 'text_input';
  const hasAdditionalText =
    Array.isArray(node.additional_fields) &&
    node.additional_fields.some((f) => f.type === 'text');

  return {
    id: node.id,
    type: node.type,
    question_text: node.question_text,
    options,
    hasTextInput: isTextType || hasAdditionalText,
    minValue: node.min_value,
    maxValue: node.max_value,
  };
}

interface AnalysisStore {
  // Данные опросника
  surveyId: number | null;
  surveyName: string;
  questions: QuestionItem[];

  // Правила
  rules: AnalysisRule[];
  selectedRuleId: string | null;

  // Состояние UI
  isLoading: boolean;
  isSaving: boolean;
  isDirty: boolean;
  error: string | null;
  successMessage: string | null;

  // Действия
  loadSurvey: (surveyId: number) => Promise<void>;
  loadRules: (surveyId: number) => Promise<void>;
  saveRules: () => Promise<void>;

  // CRUD правил
  addRule: () => void;
  deleteRule: (ruleId: string) => void;
  selectRule: (ruleId: string | null) => void;
  updateRuleName: (ruleId: string, name: string) => void;
  updateRuleMessage: (ruleId: string, message: string) => void;
  updateRuleTriggerMode: (ruleId: string, mode: 'any' | 'all') => void;

  // Работа с триггерами
  toggleTrigger: (ruleId: string, nodeId: string, optionValue: string) => void;
  isTriggerActive: (ruleId: string, nodeId: string, optionValue: string) => boolean;

  // Текстовые триггеры (match_mode = 'contains')
  setTextTrigger: (ruleId: string, nodeId: string, text: string) => void;
  removeTextTrigger: (ruleId: string, nodeId: string) => void;
  getTextTriggerValue: (ruleId: string, nodeId: string) => string | null;

  // Числовые триггеры для слайдера/шкалы (match_mode = 'gte')
  setSliderTrigger: (ruleId: string, nodeId: string, value: string) => void;
  removeSliderTrigger: (ruleId: string, nodeId: string) => void;
  getSliderTriggerValue: (ruleId: string, nodeId: string) => string | null;

  // Сброс
  reset: () => void;
}

const initialState = {
  surveyId: null as number | null,
  surveyName: '',
  questions: [] as QuestionItem[],
  rules: [] as AnalysisRule[],
  selectedRuleId: null as string | null,
  isLoading: false,
  isSaving: false,
  isDirty: false,
  error: null as string | null,
  successMessage: null as string | null,
};

export const useAnalysisStore = create<AnalysisStore>()((set, get) => ({
  ...initialState,

  loadSurvey: async (surveyId: number) => {
    set({ isLoading: true, error: null, surveyId });

    try {
      // Загрузка структуры опросника
      const surveyRes = await fetchWithAuth(`${API_BASE}/surveys/${surveyId}`);
      if (!surveyRes.ok) throw new Error('Не удалось загрузить опросник');

      const surveyData: SurveyStructureMinimal = await surveyRes.json();

      // Строим карту узлов
      const nodesMap = new Map<string, RawSurveyNode>();
      for (const n of surveyData.nodes) {
        nodesMap.set(n.id, n);
      }

      // Обход графа от start_node по самому длинному пути
      const orderedIds = traverseGraphLongestPath(
        nodesMap,
        surveyData.start_node,
      );

      // Конвертируем узлы в QuestionItem, сохраняя порядок обхода
      const questions: QuestionItem[] = [];
      for (const nodeId of orderedIds) {
        const raw = nodesMap.get(nodeId);
        if (!raw) continue;
        const item = rawNodeToQuestionItem(raw);
        if (item) questions.push(item);
      }

      set({
        surveyName: surveyData.name,
        questions,
      });

      // Загружаем правила
      await get().loadRules(surveyId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Ошибка загрузки' });
    } finally {
      set({ isLoading: false });
    }
  },

  loadRules: async (surveyId: number) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/surveys/${surveyId}/analysis-rules`);
      if (!res.ok) throw new Error('Не удалось загрузить правила анализа');

      const data = await res.json();
      set({ rules: data.rules || [], isDirty: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Ошибка загрузки правил' });
    }
  },

  saveRules: async () => {
    const { surveyId, rules } = get();
    if (!surveyId) return;

    set({ isSaving: true, error: null, successMessage: null });

    try {
      const res = await fetchWithAuth(`${API_BASE}/surveys/${surveyId}/analysis-rules`, {
        method: 'PUT',
        body: JSON.stringify({ rules }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Ошибка сохранения');
      }

      set({ isDirty: false, successMessage: 'Правила успешно сохранены' });

      // Автоскрытие уведомления об успехе
      setTimeout(() => set({ successMessage: null }), 3000);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Ошибка сохранения' });
    } finally {
      set({ isSaving: false });
    }
  },

  addRule: () => {
    const newRule: AnalysisRule = {
      id: generateRuleId(),
      name: 'Новое правило',
      triggers: [],
      trigger_mode: 'any',
      message: '',
    };

    set((state) => ({
      rules: [...state.rules, newRule],
      selectedRuleId: newRule.id,
      isDirty: true,
    }));
  },

  deleteRule: (ruleId: string) => {
    set((state) => ({
      rules: state.rules.filter((r) => r.id !== ruleId),
      selectedRuleId: state.selectedRuleId === ruleId ? null : state.selectedRuleId,
      isDirty: true,
    }));
  },

  selectRule: (ruleId: string | null) => {
    set({ selectedRuleId: ruleId });
  },

  updateRuleName: (ruleId: string, name: string) => {
    set((state) => ({
      rules: state.rules.map((r) => (r.id === ruleId ? { ...r, name } : r)),
      isDirty: true,
    }));
  },

  updateRuleMessage: (ruleId: string, message: string) => {
    set((state) => ({
      rules: state.rules.map((r) => (r.id === ruleId ? { ...r, message } : r)),
      isDirty: true,
    }));
  },

  updateRuleTriggerMode: (ruleId: string, mode: 'any' | 'all') => {
    set((state) => ({
      rules: state.rules.map((r) => (r.id === ruleId ? { ...r, trigger_mode: mode } : r)),
      isDirty: true,
    }));
  },

  toggleTrigger: (ruleId: string, nodeId: string, optionValue: string) => {
    set((state) => ({
      rules: state.rules.map((r) => {
        if (r.id !== ruleId) return r;

        const exists = r.triggers.some(
          (t) => t.node_id === nodeId && t.option_value === optionValue
        );

        const newTriggers: AnalysisTrigger[] = exists
          ? r.triggers.filter(
              (t) => !(t.node_id === nodeId && t.option_value === optionValue)
            )
          : [...r.triggers, { node_id: nodeId, option_value: optionValue }];

        return { ...r, triggers: newTriggers };
      }),
      isDirty: true,
    }));
  },

  isTriggerActive: (ruleId: string, nodeId: string, optionValue: string) => {
    const rule = get().rules.find((r) => r.id === ruleId);
    if (!rule) return false;
    return rule.triggers.some(
      (t) => t.node_id === nodeId && t.option_value === optionValue && t.match_mode !== 'contains'
    );
  },

  setTextTrigger: (ruleId: string, nodeId: string, text: string) => {
    set((state) => ({
      rules: state.rules.map((r) => {
        if (r.id !== ruleId) return r;

        // Удаляем старый текстовый триггер для этого node_id (если был)
        const filtered = r.triggers.filter(
          (t) => !(t.node_id === nodeId && t.match_mode === 'contains'),
        );

        return {
          ...r,
          triggers: [
            ...filtered,
            { node_id: nodeId, option_value: text, match_mode: 'contains' as const },
          ],
        };
      }),
      isDirty: true,
    }));
  },

  removeTextTrigger: (ruleId: string, nodeId: string) => {
    set((state) => ({
      rules: state.rules.map((r) => {
        if (r.id !== ruleId) return r;
        return {
          ...r,
          triggers: r.triggers.filter(
            (t) => !(t.node_id === nodeId && t.match_mode === 'contains'),
          ),
        };
      }),
      isDirty: true,
    }));
  },

  getTextTriggerValue: (ruleId: string, nodeId: string) => {
    const rule = get().rules.find((r) => r.id === ruleId);
    if (!rule) return null;
    const trigger = rule.triggers.find(
      (t) => t.node_id === nodeId && t.match_mode === 'contains',
    );
    return trigger ? trigger.option_value : null;
  },

  setSliderTrigger: (ruleId: string, nodeId: string, value: string) => {
    set((state) => ({
      rules: state.rules.map((r) => {
        if (r.id !== ruleId) return r;

        // Удаляем старый числовой триггер для этого node_id (если был)
        const filtered = r.triggers.filter(
          (t) => !(t.node_id === nodeId && t.match_mode === 'gte'),
        );

        return {
          ...r,
          triggers: [
            ...filtered,
            { node_id: nodeId, option_value: value, match_mode: 'gte' as const },
          ],
        };
      }),
      isDirty: true,
    }));
  },

  removeSliderTrigger: (ruleId: string, nodeId: string) => {
    set((state) => ({
      rules: state.rules.map((r) => {
        if (r.id !== ruleId) return r;
        return {
          ...r,
          triggers: r.triggers.filter(
            (t) => !(t.node_id === nodeId && t.match_mode === 'gte'),
          ),
        };
      }),
      isDirty: true,
    }));
  },

  getSliderTriggerValue: (ruleId: string, nodeId: string) => {
    const rule = get().rules.find((r) => r.id === ruleId);
    if (!rule) return null;
    const trigger = rule.triggers.find(
      (t) => t.node_id === nodeId && t.match_mode === 'gte',
    );
    return trigger ? trigger.option_value : null;
  },

  reset: () => set(initialState),
}));
