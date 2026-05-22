// ============================================
// Редактор системного анализа для врача
// ============================================
// Позволяет настраивать правила-триггеры: при каких ответах
// пациента в итоговый отчёт попадёт предупреждающий блок.

import { useCallback, useEffect, useState } from 'react';
import {
  ArrowLeft,
  Save,
  Plus,
  Trash2,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Settings2,
  Type,
} from 'lucide-react';
import { useAnalysisStore } from './store';
import type { RuleColor } from './types';

// ── Палитра цветов правил (для отчёта) ──
const RULE_COLOR_MAP: Record<string, { dot: string; bg: string; border: string; text: string; label: string; emoji: string }> = {
  red:    { dot: '#ef4444', bg: '#fef2f2', border: '#fca5a5', text: '#991b1b', label: '🔴 Красный',   emoji: '🔴' },
  orange: { dot: '#f97316', bg: '#fff7ed', border: '#fdba74', text: '#9a3412', label: '🟠 Оранжевый', emoji: '🟠' },
  yellow: { dot: '#eab308', bg: '#fefce8', border: '#fde047', text: '#854d0e', label: '🟡 Жёлтый',    emoji: '🟡' },
  green:  { dot: '#22c55e', bg: '#f0fdf4', border: '#86efac', text: '#166534', label: '🟢 Зелёный',   emoji: '🟢' },
};

const RULE_COLORS = ['red', 'orange', 'yellow', 'green'] as const;

// ── Типы узлов: читаемые названия ──
const NODE_TYPE_LABELS: Record<string, string> = {
  single_choice: 'Один выбор',
  multi_choice: 'Множественный выбор',
  multi_choice_with_input: 'Выбор + ввод',
  slider: 'Слайдер',
  scale_1_10: 'Шкала 1–10',
  body_map: 'Карта тела',
  text_input: 'Текстовый ввод',
};

interface AnalysisEditorProps {
  surveyId: number;
}

const AnalysisEditor = ({ surveyId }: AnalysisEditorProps) => {
  const {
    surveyName,
    questions,
    rules,
    selectedRuleId,
    isLoading,
    isSaving,
    isDirty,
    error,
    successMessage,
    loadSurvey,
    saveRules,
    addRule,
    deleteRule,
    selectRule,
    updateRuleName,
    updateRuleMessage,
    updateRuleTriggerMode,
    updateRuleColor,
    toggleTrigger,
    isTriggerActive,
    setTextTrigger,
    removeTextTrigger,
    getTextTriggerValue,
    setSliderTrigger,
    removeSliderTrigger,
    getSliderTriggerValue,
    reset,
  } = useAnalysisStore();

  // Загрузка данных
  useEffect(() => {
    loadSurvey(surveyId);
    return () => reset();
  }, [surveyId, loadSurvey, reset]);

  // Горячие клавиши
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveRules();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [saveRules]);

  // Предупреждение при уходе со страницы
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  const selectedRule = rules.find((r) => r.id === selectedRuleId) || null;

  const handleBack = useCallback(() => {
    if (isDirty && !window.confirm('Есть несохранённые изменения. Уйти?')) return;
    window.location.href = '/admin/surveys';
  }, [isDirty]);

  // ── Загрузка ──
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-3 text-slate-500">Загрузка опросника…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-100 overflow-hidden">
      {/* ═══════ Toolbar ═══════ */}
      <header className="flex items-center justify-between bg-white border-b border-slate-200 px-4 py-2.5 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            Назад
          </button>

          <div className="h-5 w-px bg-slate-300" />

          <div className="flex items-center gap-2">
            <Settings2 size={18} className="text-amber-600" />
            <span className="font-semibold text-slate-900 text-sm">
              Системный анализ
            </span>
            {surveyName && (
              <span className="text-slate-400 text-sm">— {surveyName}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Уведомления */}
          {successMessage && (
            <span className="flex items-center gap-1 text-green-600 text-xs font-medium">
              <CheckCircle size={14} /> {successMessage}
            </span>
          )}
          {error && (
            <span className="flex items-center gap-1 text-red-500 text-xs font-medium">
              <AlertTriangle size={14} /> {error}
            </span>
          )}

          {isDirty && (
            <span className="text-xs text-amber-500 font-medium">
              Есть изменения
            </span>
          )}

          <button
            onClick={saveRules}
            disabled={isSaving || !isDirty}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm font-medium
                       hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save size={14} />
            {isSaving ? 'Сохранение…' : 'Сохранить'}
          </button>
        </div>
      </header>

      {/* ═══════ Main content ═══════ */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Левая панель: список правил ── */}
        <aside className="w-72 bg-white border-r border-slate-200 flex flex-col shrink-0">
          <div className="p-3 border-b border-slate-100">
            <button
              onClick={addRule}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg
                         text-sm font-medium hover:bg-blue-100 transition-colors"
            >
              <Plus size={16} />
              Добавить правило
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {rules.length === 0 ? (
              <div className="p-4 text-center text-slate-400 text-sm">
                Нет правил. Создайте первое правило,
                чтобы настроить системный анализ.
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {rules.map((rule) => (
                  <li
                    key={rule.id}
                    onClick={() => selectRule(rule.id)}
                    className={`flex items-center justify-between px-3 py-2.5 cursor-pointer transition-colors
                      ${
                        selectedRuleId === rule.id
                          ? 'bg-blue-50 border-l-2 border-blue-600'
                          : 'hover:bg-slate-50 border-l-2 border-transparent'
                      }`}
                  >
                    <div className="min-w-0 flex-1 flex items-center gap-2">
                      <span
                        className="shrink-0 w-3 h-3 rounded-full"
                        style={{ background: RULE_COLOR_MAP[rule.color || 'red']?.dot }}
                        title={RULE_COLOR_MAP[rule.color || 'red']?.label}
                      />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">
                          {rule.name || 'Без названия'}
                        </p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {rule.triggers.length}{' '}
                          {triggerDeclension(rule.triggers.length)} ·{' '}
                          {rule.trigger_mode === 'all' ? 'ВСЕ' : 'ЛЮБОЙ'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0 ml-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm(`Удалить правило «${rule.name}»?`))
                            deleteRule(rule.id);
                        }}
                        className="p-1 text-slate-300 hover:text-red-500 transition-colors"
                        title="Удалить"
                      >
                        <Trash2 size={14} />
                      </button>
                      <ChevronRight
                        size={14}
                        className={`text-slate-300 ${
                          selectedRuleId === rule.id ? 'text-blue-500' : ''
                        }`}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        {/* ── Правая панель: редактор правила ── */}
        <main className="flex-1 overflow-y-auto p-5">
          {!selectedRule ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-slate-400">
                <Settings2 size={40} className="mx-auto mb-3 opacity-40" />
                <p className="text-sm">
                  Выберите правило из списка слева
                  <br />
                  или создайте новое
                </p>
              </div>
            </div>
          ) : (
            <RuleEditor
              rule={selectedRule}
              questions={questions}
              onUpdateName={(name) => updateRuleName(selectedRule.id, name)}
              onUpdateMessage={(msg) => updateRuleMessage(selectedRule.id, msg)}
              onUpdateMode={(mode) => updateRuleTriggerMode(selectedRule.id, mode)}
              onUpdateColor={(color) => updateRuleColor(selectedRule.id, color)}
              onToggleTrigger={(nodeId, optionValue) =>
                toggleTrigger(selectedRule.id, nodeId, optionValue)
              }
              isTriggerActive={(nodeId, optionValue) =>
                isTriggerActive(selectedRule.id, nodeId, optionValue)
              }
              onSetTextTrigger={(nodeId, text) =>
                setTextTrigger(selectedRule.id, nodeId, text)
              }
              onRemoveTextTrigger={(nodeId) =>
                removeTextTrigger(selectedRule.id, nodeId)
              }
              getTextTriggerValue={(nodeId) =>
                getTextTriggerValue(selectedRule.id, nodeId)
              }
              onSetSliderTrigger={(nodeId, value) =>
                setSliderTrigger(selectedRule.id, nodeId, value)
              }
              onRemoveSliderTrigger={(nodeId) =>
                removeSliderTrigger(selectedRule.id, nodeId)
              }
              getSliderTriggerValue={(nodeId) =>
                getSliderTriggerValue(selectedRule.id, nodeId)
              }
            />
          )}
        </main>
      </div>
    </div>
  );
};

// ================================================================
// Компонент редактора одного правила
// ================================================================

interface RuleEditorProps {
  rule: {
    id: string;
    name: string;
    triggers: { node_id: string; option_value: string; match_mode?: 'exact' | 'contains' | 'gte' }[];
    trigger_mode: 'any' | 'all';
    message: string;
    color?: string;
  };
  questions: {
    id: string;
    type: string;
    question_text: string;
    options: { id: string; text: string; value: string }[];
    hasTextInput: boolean;
    minValue?: number;
    maxValue?: number;
  }[];
  onUpdateName: (name: string) => void;
  onUpdateMessage: (msg: string) => void;
  onUpdateMode: (mode: 'any' | 'all') => void;
  onUpdateColor: (color: RuleColor) => void;
  onToggleTrigger: (nodeId: string, optionValue: string) => void;
  onSetTextTrigger: (nodeId: string, text: string) => void;
  onRemoveTextTrigger: (nodeId: string) => void;
  isTriggerActive: (nodeId: string, optionValue: string) => boolean;
  getTextTriggerValue: (nodeId: string) => string | null;
  onSetSliderTrigger: (nodeId: string, value: string) => void;
  onRemoveSliderTrigger: (nodeId: string) => void;
  getSliderTriggerValue: (nodeId: string) => string | null;
}

const RuleEditor = ({
  rule,
  questions,
  onUpdateName,
  onUpdateMessage,
  onUpdateMode,
  onUpdateColor,
  onToggleTrigger,
  onSetTextTrigger,
  onRemoveTextTrigger,
  isTriggerActive,
  getTextTriggerValue,
  onSetSliderTrigger,
  onRemoveSliderTrigger,
  getSliderTriggerValue,
}: RuleEditorProps) => {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* ── Название и режим ── */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
          Название правила
        </label>
        <input
          type="text"
          value={rule.name}
          onChange={(e) => onUpdateName(e.target.value)}
          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
          placeholder="Например: Высокая интенсивность боли"
        />

        <div className="mt-4">
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            Режим срабатывания между вопросами
          </label>
          <div className="flex gap-3">
            <label
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-colors
                ${
                  rule.trigger_mode === 'any'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
            >
              <input
                type="radio"
                name={`mode_${rule.id}`}
                checked={rule.trigger_mode === 'any'}
                onChange={() => onUpdateMode('any')}
                className="sr-only"
              />
              <span className="font-medium">Любой</span>
              <span className="text-xs opacity-70">хотя бы один ответ</span>
            </label>

            <label
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-colors
                ${
                  rule.trigger_mode === 'all'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
            >
              <input
                type="radio"
                name={`mode_${rule.id}`}
                checked={rule.trigger_mode === 'all'}
                onChange={() => onUpdateMode('all')}
                className="sr-only"
              />
              <span className="font-medium">Все вопросы</span>
              <span className="text-xs opacity-70">хотя бы по одному в каждом</span>
            </label>
          </div>
          <p className="mt-2 text-xs text-slate-400 leading-relaxed">
            {rule.trigger_mode === 'any'
              ? 'Правило сработает, если хотя бы один из выбранных ответов совпадёт.'
              : 'Правило сработает, если в каждом вопросе с триггерами совпадёт хотя бы один ответ (ИЛИ внутри вопроса, И между вопросами).'}
          </p>
        </div>

        {/* ── Цвет правила (для отчёта) ── */}
        <div className="mt-4">
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            Цвет в отчёте
          </label>
          <div className="flex items-center gap-2">
            {RULE_COLORS.map((c) => {
              const palette = RULE_COLOR_MAP[c];
              const active = (rule.color || 'red') === c;
              return (
                <button
                  key={c}
                  type="button"
                  onClick={() => onUpdateColor(c)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm transition-colors cursor-pointer
                    ${active
                      ? 'ring-2 ring-offset-1'
                      : 'hover:bg-slate-50'
                    }`}
                  style={{
                    borderColor: active ? palette.dot : undefined,
                    background: active ? palette.bg : undefined,
                    color: active ? palette.text : undefined,
                    // @ts-expect-error custom css variable
                    '--tw-ring-color': active ? palette.dot : undefined,
                  }}
                  title={palette.label}
                >
                  <span
                    className="w-3.5 h-3.5 rounded-full border border-white/50 shrink-0"
                    style={{ background: palette.dot }}
                  />
                  <span className="font-medium">{palette.label}</span>
                </button>
              );
            })}
          </div>
          <p className="mt-1.5 text-xs text-slate-400">
            Выбранный цвет будет использован для фона блока триггера в итоговом отчёте для врача.
          </p>
        </div>
      </div>

      {/* ── Дерево вопросов / триггеры ── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-4 py-3 border-b border-slate-100">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Триггеры — вопросы и ответы
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Отметьте ответы, которые должны активировать это правило
          </p>
        </div>

        <div className="divide-y divide-slate-100 max-h-[50vh] overflow-y-auto">
          {questions.length === 0 ? (
            <p className="p-4 text-sm text-slate-400 text-center">
              Нет вопросов в опроснике
            </p>
          ) : (
            questions.map((q) => (
              <QuestionBlock
                key={q.id}
                question={q}
                onToggle={(optionValue) => onToggleTrigger(q.id, optionValue)}
                isActive={(optionValue) => isTriggerActive(q.id, optionValue)}
                onSetTextTrigger={(text) => onSetTextTrigger(q.id, text)}
                onRemoveTextTrigger={() => onRemoveTextTrigger(q.id)}
                textTriggerValue={getTextTriggerValue(q.id)}
                onSetSliderTrigger={(value) => onSetSliderTrigger(q.id, value)}
                onRemoveSliderTrigger={() => onRemoveSliderTrigger(q.id)}
                sliderTriggerValue={getSliderTriggerValue(q.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* ── Текст сообщения ── */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
          Текст сообщения для врача
        </label>
        <textarea
          value={rule.message}
          onChange={(e) => onUpdateMessage(e.target.value)}
          rows={4}
          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm resize-y
                     focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
          placeholder="Текст, который увидит врач в отчёте, если триггеры сработают…"
        />
        <p className="mt-1 text-xs text-slate-400">
          Это сообщение будет выведено в блоке «Системный анализ для врача» в начале отчёта.
        </p>
      </div>

      {/* ── Превью ── */}
      {rule.message.trim() && rule.triggers.length > 0 && (() => {
        const palette = RULE_COLOR_MAP[rule.color || 'red'];
        return (
          <div
            className="rounded-xl p-4"
            style={{
              background: palette.bg,
              border: `2px solid ${palette.border}`,
            }}
          >
            <h4
              className="text-xs font-bold uppercase tracking-wide mb-2 flex items-center gap-1.5"
              style={{ color: palette.text }}
            >
              <AlertTriangle size={14} />
              Превью блока в отчёте
            </h4>
            <div
              className="text-sm leading-relaxed"
              style={{ color: palette.text }}
            >
              {rule.message}
            </div>
          </div>
        );
      })()}
    </div>
  );
};

// ================================================================
// Блок одного вопроса в дереве
// ================================================================

interface QuestionBlockProps {
  question: {
    id: string;
    type: string;
    question_text: string;
    options: { id: string; text: string; value: string }[];
    hasTextInput: boolean;
    minValue?: number;
    maxValue?: number;
  };
  onToggle: (optionValue: string) => void;
  isActive: (optionValue: string) => boolean;
  onSetTextTrigger: (text: string) => void;
  onRemoveTextTrigger: () => void;
  textTriggerValue: string | null;
  onSetSliderTrigger: (value: string) => void;
  onRemoveSliderTrigger: () => void;
  sliderTriggerValue: string | null;
}

const SLIDER_TYPES = new Set(['slider', 'scale_1_10']);

const QuestionBlock = ({
  question,
  onToggle,
  isActive,
  onSetTextTrigger,
  onRemoveTextTrigger,
  textTriggerValue,
  onSetSliderTrigger,
  onRemoveSliderTrigger,
  sliderTriggerValue,
}: QuestionBlockProps) => {
  const isSlider = SLIDER_TYPES.has(question.type);
  const activeOptionCount = question.options.filter((o) => isActive(o.value || o.id)).length;
  const anyOptionActive = activeOptionCount > 0;
  const hasTextTrigger = textTriggerValue !== null;
  const hasSliderTrigger = sliderTriggerValue !== null;
  const anyActive = anyOptionActive || hasTextTrigger || hasSliderTrigger;

  // Локальное состояние для ввода текста триггера
  const [localText, setLocalText] = useState(textTriggerValue ?? '');
  const [isTextExpanded, setIsTextExpanded] = useState(hasTextTrigger);

  // Локальное состояние для слайдера
  const [localSlider, setLocalSlider] = useState(sliderTriggerValue ?? '');
  const [isSliderExpanded, setIsSliderExpanded] = useState(hasSliderTrigger);

  // Синхронизация при смене правила
  useEffect(() => {
    setLocalText(textTriggerValue ?? '');
    setIsTextExpanded(textTriggerValue !== null);
  }, [textTriggerValue]);

  useEffect(() => {
    setLocalSlider(sliderTriggerValue ?? '');
    setIsSliderExpanded(sliderTriggerValue !== null);
  }, [sliderTriggerValue]);

  const handleTextSave = () => {
    const trimmed = localText.trim();
    if (trimmed) {
      onSetTextTrigger(trimmed);
    } else {
      onRemoveTextTrigger();
      setIsTextExpanded(false);
    }
  };

  const handleTextRemove = () => {
    onRemoveTextTrigger();
    setLocalText('');
    setIsTextExpanded(false);
  };

  const handleSliderSave = () => {
    const trimmed = localSlider.trim();
    if (trimmed && !isNaN(Number(trimmed))) {
      onSetSliderTrigger(trimmed);
    } else {
      onRemoveSliderTrigger();
      setIsSliderExpanded(false);
    }
  };

  const handleSliderRemove = () => {
    onRemoveSliderTrigger();
    setLocalSlider('');
    setIsSliderExpanded(false);
  };

  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-2 mb-2">
        <span
          className="shrink-0 mt-0.5 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded"
          style={{ background: '#e0e7ff', color: '#3730a3' }}
        >
          {NODE_TYPE_LABELS[question.type] || question.type}
        </span>
        <p className="text-sm font-medium text-slate-800 leading-snug">
          {question.question_text}
        </p>
        {anyActive && (
          <span className="shrink-0 ml-auto text-[10px] font-bold text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded">
            ТРИГГЕР
          </span>
        )}
      </div>

      {/* Варианты ответа (чекбоксы) — для вопросов с options */}
      {question.options.length > 0 && (
        <div className="ml-1">
          {/* Заголовок секции с OR-индикатором */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold">
              Варианты
            </span>
            {activeOptionCount > 1 ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-orange-700 bg-orange-100 border border-orange-200 px-1.5 py-0.5 rounded">
                <span className="opacity-60">🔀</span>
                {activeOptionCount} выбрано · ИЛИ
              </span>
            ) : (
              <span className="text-[10px] text-slate-300 italic">
                можно выбрать несколько (логика ИЛИ)
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
            {question.options.map((opt, idx) => {
              const val = opt.value || opt.id;
              const active = isActive(val);
              const isLastActive =
                active &&
                activeOptionCount > 1 &&
                question.options
                  .slice(idx + 1)
                  .every((o) => !isActive(o.value || o.id));
              return (
                <div key={opt.id} className="relative">
                  <label
                    className={`flex items-center gap-2 px-2.5 py-1.5 rounded-md cursor-pointer text-sm transition-colors
                      ${active ? 'bg-amber-50 text-amber-900 ring-1 ring-amber-200' : 'text-slate-600 hover:bg-slate-50'}`}
                  >
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() => onToggle(val)}
                      className="rounded border-slate-300 text-amber-500 focus:ring-amber-400 w-4 h-4"
                    />
                    <span>{opt.text}</span>
                    {active && activeOptionCount > 1 && !isLastActive && (
                      <span className="ml-auto text-[9px] font-bold text-orange-400 shrink-0">
                        ИЛИ
                      </span>
                    )}
                  </label>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Числовой триггер — для slider / scale вопросов */}
      {isSlider && (
        <div className="ml-1 mt-1">
          {!isSliderExpanded ? (
            <button
              onClick={() => setIsSliderExpanded(true)}
              className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 transition-colors"
            >
              <Plus size={12} />
              Добавить числовой триггер (значение ≥ порога)
            </button>
          ) : (
            <div className="flex items-center gap-2 p-2 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-slate-500 uppercase tracking-wide font-semibold mb-1.5">
                  Сработает если значение ≥
                </p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={localSlider}
                    onChange={(e) => setLocalSlider(e.target.value)}
                    onBlur={handleSliderSave}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSliderSave();
                    }}
                    min={question.minValue ?? 1}
                    max={question.maxValue ?? 10}
                    step={1}
                    className="w-20 px-2 py-1 border border-slate-200 rounded text-sm text-center
                               focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
                    placeholder={String(question.minValue ?? 1)}
                  />
                  <input
                    type="range"
                    value={localSlider || String(question.minValue ?? 1)}
                    onChange={(e) => {
                      setLocalSlider(e.target.value);
                      onSetSliderTrigger(e.target.value);
                    }}
                    min={question.minValue ?? 1}
                    max={question.maxValue ?? 10}
                    step={1}
                    className="flex-1 h-2 accent-amber-500"
                  />
                  <span className="text-xs text-slate-400 shrink-0">
                    {question.minValue ?? 1}–{question.maxValue ?? 10}
                  </span>
                </div>
                {hasSliderTrigger && (
                  <p className="text-xs text-amber-700 mt-1">
                    Триггер: значение ≥ <strong>{sliderTriggerValue}</strong>
                  </p>
                )}
              </div>
              <button
                onClick={handleSliderRemove}
                className="shrink-0 p-1 text-slate-300 hover:text-red-500 transition-colors"
                title="Удалить числовой триггер"
              >
                <Trash2 size={14} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Текстовый триггер — для text_input и вопросов с additional_fields */}
      {question.hasTextInput && (
        <div className="ml-1 mt-2">
          {!isTextExpanded ? (
            <button
              onClick={() => setIsTextExpanded(true)}
              className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 transition-colors"
            >
              <Type size={12} />
              Добавить текстовый триггер (содержит подстроку)
            </button>
          ) : (
            <div className="flex items-start gap-2 p-2 bg-slate-50 rounded-lg border border-slate-200">
              <Type size={14} className="shrink-0 mt-1.5 text-slate-400" />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-slate-500 uppercase tracking-wide font-semibold mb-1">
                  Сработает если ответ содержит:
                </p>
                <input
                  type="text"
                  value={localText}
                  onChange={(e) => setLocalText(e.target.value)}
                  onBlur={handleTextSave}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleTextSave();
                  }}
                  className="w-full px-2 py-1 border border-slate-200 rounded text-sm
                             focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
                  placeholder="Введите подстроку для поиска в ответе…"
                />
              </div>
              <button
                onClick={handleTextRemove}
                className="shrink-0 p-1 text-slate-300 hover:text-red-500 transition-colors mt-1"
                title="Удалить текстовый триггер"
              >
                <Trash2 size={14} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ================================================================
// Утилита: склонение слова «триггер»
// ================================================================
function triggerDeclension(n: number): string {
  const abs = Math.abs(n) % 100;
  const last = abs % 10;
  if (abs >= 11 && abs <= 19) return 'триггеров';
  if (last === 1) return 'триггер';
  if (last >= 2 && last <= 4) return 'триггера';
  return 'триггеров';
}

export default AnalysisEditor;
