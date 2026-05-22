import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  Check,
  FlaskConical,
  Plus,
  RefreshCw,
  Route,
  Save,
  Search,
  Sun,
  Trash2,
  X,
} from 'lucide-react'

import {
  getAdminBaseUrl,
  createRoutingRule,
  deleteRoutingRule,
  getCrmFieldOptions,
  getCrmFields,
  getRoutingClinic,
  getRoutingClinics,
  getRoutingSurveys,
  reorderRoutingRules,
  saveRoutingClinicSettings,
  syncCrmFields,
  testDealRouting,
  updateRoutingRule,
} from '@/api'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import type {
  CrmFieldItem,
  CrmFieldOptionItem,
  RoutingClinicDetailResponse,
  RoutingClinicItem,
  RoutingCondition,
  RoutingConditionLogic,
  RoutingOperator,
  RoutingRule,
  RoutingRulePayload,
  RoutingSurveyListItem,
  RoutingTestDealResponse,
} from '@/types'

const OPERATOR_LABELS: Record<RoutingOperator, string> = {
  equals: 'равно',
  not_equals: 'не равно',
  contains: 'содержит',
  not_contains: 'не содержит',
  is_filled: 'заполнено',
  is_empty: 'не заполнено',
}

const OPERATORS = Object.keys(OPERATOR_LABELS) as RoutingOperator[]

const CRM_FIELD_ID_PATTERN = /^UF_CRM_\d+$/i
const ADMIN_URL = getAdminBaseUrl()

function isTechnicalCrmFieldTitle(field: CrmFieldItem): boolean {
  return CRM_FIELD_ID_PATTERN.test(field.title.trim()) || field.title.trim() === field.field_id
}

function formatCrmFieldTitle(field: CrmFieldItem): string {
  return isTechnicalCrmFieldTitle(field) ? field.field_id : field.title
}

const emptyCondition = (): RoutingCondition => ({
  crm_field_id: '',
  operator: 'equals',
  value: '',
})

const emptyRuleForm = (surveyId = 0): RoutingRulePayload => ({
  name: '',
  is_active: true,
  survey_config_id: surveyId,
  condition_logic: 'AND',
  priority: null,
  conditions: [emptyCondition()],
})

function formatCondition(
  condition: RoutingCondition,
  fieldsById: Map<string, CrmFieldItem>,
  optionsByField: Record<string, CrmFieldOptionItem[]>
): string {
  const field = fieldsById.get(condition.crm_field_id)
  const fieldTitle = field ? formatCrmFieldTitle(field) : condition.crm_field_id
  const operator = OPERATOR_LABELS[condition.operator]

  if (condition.operator === 'is_filled' || condition.operator === 'is_empty') {
    return `${fieldTitle} ${operator}`
  }

  const option = optionsByField[condition.crm_field_id]?.find(
    (item) => item.option_id === String(condition.value ?? '')
  )
  const value = option?.label ?? String(condition.value ?? '')
  return `${fieldTitle} ${operator} ${value}`
}

export default function SurveyRoutingPage() {
  const { isAuthenticated, isChecking } = useAdminAuth()
  const [clinics, setClinics] = useState<RoutingClinicItem[]>([])
  const [activeClinicKey, setActiveClinicKey] = useState('')
  const [detail, setDetail] = useState<RoutingClinicDetailResponse | null>(null)
  const [surveys, setSurveys] = useState<RoutingSurveyListItem[]>([])
  const [crmFields, setCrmFields] = useState<CrmFieldItem[]>([])
  const [fieldSearch, setFieldSearch] = useState('')
  const [optionsByField, setOptionsByField] = useState<Record<string, CrmFieldOptionItem[]>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null)
  const [ruleForm, setRuleForm] = useState<RoutingRulePayload>(emptyRuleForm())
  const [advancedMode, setAdvancedMode] = useState(false)
  const [dealId, setDealId] = useState('')
  const [testResult, setTestResult] = useState<RoutingTestDealResponse | null>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [isDarkTheme, setIsDarkTheme] = useState(false)

  const fieldsById = useMemo(
    () => new Map(crmFields.map((field) => [field.field_id, field])),
    [crmFields]
  )

  const activeClinic = detail?.clinic
  const firstSurveyId = surveys[0]?.id ?? 0

  const loadClinics = useCallback(async () => {
    const response = await getRoutingClinics()
    setClinics(response.items)
    setActiveClinicKey((current) => current || response.items[0]?.key || '')
  }, [])

  const loadClinic = useCallback(async (clinicKey: string) => {
    if (!clinicKey) return
    const response = await getRoutingClinic(clinicKey)
    setDetail(response)
  }, [])

  const loadCrmFields = useCallback(async (search = '') => {
    const response = await getCrmFields(search)
    setCrmFields(response.items)
  }, [])

  const loadFieldOptions = useCallback(
    async (fieldId: string) => {
      if (!fieldId || optionsByField[fieldId]) return
      const response = await getCrmFieldOptions(fieldId)
      setOptionsByField((current) => ({
        ...current,
        [fieldId]: response.items,
      }))
    },
    [optionsByField]
  )

  useEffect(() => {
    if (!isAuthenticated) return
    setIsLoading(true)
    setError(null)
    setWarning(null)

    Promise.all([loadClinics(), getRoutingSurveys(), loadCrmFields()])
      .then(([, surveyItems]) => {
        setSurveys(surveyItems)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Ошибка загрузки'))
      .finally(() => setIsLoading(false))
  }, [isAuthenticated, loadClinics, loadCrmFields])

  useEffect(() => {
    if (!activeClinicKey || !isAuthenticated) return
    loadClinic(activeClinicKey).catch((err) =>
      setError(err instanceof Error ? err.message : 'Ошибка загрузки клиники')
    )
  }, [activeClinicKey, isAuthenticated, loadClinic])

  useEffect(() => {
    const listFieldIds = ruleForm.conditions
      .map((condition) => condition.crm_field_id)
      .filter((fieldId) => fieldsById.get(fieldId)?.is_list)

    listFieldIds.forEach((fieldId) => {
      void loadFieldOptions(fieldId)
    })
  }, [fieldsById, loadFieldOptions, ruleForm.conditions])

  const refreshCurrentClinic = async () => {
    await loadClinics()
    if (activeClinicKey) {
      await loadClinic(activeClinicKey)
    }
  }

  const handleSaveSettings = async () => {
    if (!activeClinicKey || !activeClinic) return
    setIsSaving(true)
    setError(null)
    setWarning(null)
    setStatus(null)
    try {
      await saveRoutingClinicSettings(activeClinicKey, {
        default_survey_config_id: activeClinic.default_survey_config_id ?? null,
        is_enabled: activeClinic.is_enabled,
      })
      await refreshCurrentClinic()
      setStatus('Настройки клиники сохранены')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сохранения')
    } finally {
      setIsSaving(false)
    }
  }

  const updateClinicDraft = (patch: Partial<RoutingClinicItem>) => {
    setDetail((current) =>
      current
        ? {
            ...current,
            clinic: {
              ...current.clinic,
              ...patch,
            },
          }
        : current
    )
  }

  const startCreateRule = () => {
    setEditingRuleId(null)
    setRuleForm(emptyRuleForm(firstSurveyId))
    setAdvancedMode(false)
  }

  const startEditRule = (rule: RoutingRule) => {
    setEditingRuleId(rule.id)
    setRuleForm({
      name: rule.name,
      is_active: rule.is_active,
      survey_config_id: rule.survey_config_id,
      condition_logic: rule.condition_logic,
      priority: rule.priority,
      conditions: rule.conditions.length ? rule.conditions : [emptyCondition()],
    })
    setAdvancedMode(false)
  }

  const updateCondition = (index: number, patch: Partial<RoutingCondition>) => {
    setRuleForm((current) => ({
      ...current,
      conditions: current.conditions.map((condition, conditionIndex) =>
        conditionIndex === index
          ? {
              ...condition,
              ...patch,
              ...(patch.crm_field_id ? { value: '' } : {}),
            }
          : condition
      ),
    }))
  }

  const removeCondition = (index: number) => {
    setRuleForm((current) => ({
      ...current,
      conditions:
        current.conditions.length === 1
          ? [emptyCondition()]
          : current.conditions.filter((_, conditionIndex) => conditionIndex !== index),
    }))
  }

  const buildRulePayload = (): RoutingRulePayload => ({
    ...ruleForm,
    name: ruleForm.name.trim(),
    survey_config_id: Number(ruleForm.survey_config_id),
    priority: ruleForm.priority === null || ruleForm.priority === undefined ? null : Number(ruleForm.priority),
    conditions: ruleForm.conditions.map((condition) => ({
      crm_field_id: condition.crm_field_id.trim(),
      operator: condition.operator,
      value:
        condition.operator === 'is_filled' || condition.operator === 'is_empty'
          ? null
          : condition.value,
    })),
  })

  const handleSaveRule = async () => {
    if (!activeClinicKey) return
    setIsSaving(true)
    setError(null)
    setWarning(null)
    setStatus(null)
    try {
      const payload = buildRulePayload()
      if (editingRuleId) {
        await updateRoutingRule(editingRuleId, payload)
      } else {
        await createRoutingRule(activeClinicKey, payload)
      }
      await loadClinic(activeClinicKey)
      startCreateRule()
      setStatus('Правило сохранено')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сохранения правила')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteRule = async (ruleId: number) => {
    if (!confirm('Удалить правило маршрутизации?')) return
    setIsSaving(true)
    setError(null)
    setWarning(null)
    try {
      await deleteRoutingRule(ruleId)
      if (activeClinicKey) await loadClinic(activeClinicKey)
      if (editingRuleId === ruleId) startCreateRule()
      setStatus('Правило удалено')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка удаления правила')
    } finally {
      setIsSaving(false)
    }
  }

  const moveRule = async (ruleId: number, direction: 'up' | 'down') => {
    if (!detail || !activeClinicKey) return
    const rules = [...detail.rules]
    const index = rules.findIndex((rule) => rule.id === ruleId)
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (index < 0 || targetIndex < 0 || targetIndex >= rules.length) return

    const sourcePriority = rules[index].priority
    rules[index].priority = rules[targetIndex].priority
    rules[targetIndex].priority = sourcePriority

    setDetail({ ...detail, rules })
    await reorderRoutingRules(
      activeClinicKey,
      rules.map((rule) => ({ id: rule.id, priority: rule.priority }))
    )
    await loadClinic(activeClinicKey)
  }

  const handleSyncFields = async () => {
    setIsSaving(true)
    setError(null)
    setWarning(null)
    setStatus(null)
    try {
      const result = await syncCrmFields()
      if (!result.success) {
        setWarning(result.message || 'CRM-поля не были обновлены')
        return
      }
      await loadCrmFields(fieldSearch)
      setStatus(`CRM-поля обновлены: ${result.fields_updated}, варианты: ${result.options_updated}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка синхронизации CRM-полей')
    } finally {
      setIsSaving(false)
    }
  }

  const handleTestDeal = async () => {
    if (!activeClinicKey || !dealId.trim()) return
    setIsTesting(true)
    setError(null)
    setWarning(null)
    setTestResult(null)
    try {
      const result = await testDealRouting(activeClinicKey, Number(dealId))
      setTestResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка проверки сделки')
    } finally {
      setIsTesting(false)
    }
  }

  if (isChecking || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-600">
        Загрузка...
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className={`routing-page min-h-screen bg-slate-50 text-slate-900 ${isDarkTheme ? 'routing-dark' : ''}`}>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[104rem] flex-col gap-4 px-5 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-teal-600 text-white">
              <Route className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">Маршрутизация опросников</h1>
              <div className="mt-1 text-sm text-slate-500">
                Выбор опросника по клинике и полям сделки Bitrix24
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="btn-secondary inline-flex items-center gap-2 rounded-lg px-4 py-2"
              type="button"
              disabled={isSaving}
              onClick={handleSyncFields}
            >
              <RefreshCw className="h-4 w-4" />
              Обновить CRM-поля
            </button>
            <button
              className="routing-theme-toggle inline-flex h-10 w-10 items-center justify-center rounded-lg"
              type="button"
              aria-label={isDarkTheme ? 'Выключить темную тему' : 'Включить темную тему'}
              aria-pressed={isDarkTheme}
              title={isDarkTheme ? 'Выключить темную тему' : 'Включить темную тему'}
              onClick={() => setIsDarkTheme((value) => !value)}
            >
              <Sun className="h-5 w-5" />
            </button>
            <a className="btn-secondary rounded-lg px-4 py-2" href={ADMIN_URL}>
              Админка
            </a>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[104rem] gap-5 px-5 py-5 xl:grid-cols-[16rem_minmax(0,1fr)_26rem]">
        <aside className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Клиники
          </div>
          <div className="space-y-2">
            {clinics.map((clinic) => (
              <button
                key={clinic.key}
                className={`w-full rounded-md px-3 py-2 text-left text-sm font-medium transition ${
                  activeClinicKey === clinic.key
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
                type="button"
                onClick={() => setActiveClinicKey(clinic.key)}
              >
                {clinic.title}
              </button>
            ))}
          </div>
        </aside>

        <section className="space-y-5">
          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          ) : null}
          {warning ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {warning}
            </div>
          ) : null}
          {status ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              {status}
            </div>
          ) : null}

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  {activeClinic?.title || 'Клиника'}
                </div>
                <h2 className="mt-1 text-lg font-semibold">Опросник по умолчанию</h2>
              </div>
              <button
                className="btn-primary inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2"
                type="button"
                disabled={isSaving || !activeClinic}
                onClick={handleSaveSettings}
              >
                <Save className="h-4 w-4" />
                Сохранить
              </button>
            </div>

            <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_12rem]">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Опросник</span>
                <select
                  className="input-field"
                  value={activeClinic?.default_survey_config_id ?? ''}
                  onChange={(event) =>
                    updateClinicDraft({
                      default_survey_config_id: event.target.value ? Number(event.target.value) : null,
                    })
                  }
                >
                  <option value="">Не выбран</option>
                  {surveys.map((survey) => (
                    <option key={survey.id} value={survey.id}>
                      {survey.name} v{survey.version}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-end gap-2 pb-3 text-sm font-medium text-slate-700">
                <input
                  className="h-5 w-5 rounded border-slate-300 text-teal-600"
                  type="checkbox"
                  checked={activeClinic?.is_enabled ?? true}
                  onChange={(event) => updateClinicDraft({ is_enabled: event.target.checked })}
                />
                Включена
              </label>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <h2 className="text-lg font-semibold">Правила</h2>
              <button
                className="btn-secondary inline-flex items-center gap-2 rounded-lg px-3 py-2"
                type="button"
                onClick={startCreateRule}
              >
                <Plus className="h-4 w-4" />
                Новое
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-[0.08em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Приоритет</th>
                    <th className="px-4 py-3">Правило</th>
                    <th className="px-4 py-3">Опросник</th>
                    <th className="px-4 py-3">Условия</th>
                    <th className="px-4 py-3">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {detail?.rules.map((rule, index) => (
                    <tr key={rule.id} className={editingRuleId === rule.id ? 'bg-teal-50/70' : ''}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-slate-700">{rule.priority}</span>
                          <button
                            className="rounded p-1 text-slate-500 hover:bg-slate-100"
                            type="button"
                            disabled={index === 0}
                            onClick={() => void moveRule(rule.id, 'up')}
                            title="Выше"
                          >
                            <ArrowUp className="h-4 w-4" />
                          </button>
                          <button
                            className="rounded p-1 text-slate-500 hover:bg-slate-100"
                            type="button"
                            disabled={index === (detail?.rules.length ?? 1) - 1}
                            onClick={() => void moveRule(rule.id, 'down')}
                            title="Ниже"
                          >
                            <ArrowDown className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-900">{rule.name}</div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                          {rule.is_active ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700">
                              <Check className="h-3.5 w-3.5" />
                              активно
                            </span>
                          ) : (
                            <span>выключено</span>
                          )}
                          <span>{rule.condition_logic}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-700">{rule.survey_name || rule.survey_config_id}</td>
                      <td className="px-4 py-3 text-slate-600">
                        <div className="max-w-[42rem] truncate">
                          {rule.conditions
                            .map((condition) => formatCondition(condition, fieldsById, optionsByField))
                            .join(rule.condition_logic === 'AND' ? ' И ' : ' ИЛИ ')}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <button
                            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm hover:bg-slate-50"
                            type="button"
                            onClick={() => startEditRule(rule)}
                          >
                            Изменить
                          </button>
                          <button
                            className="rounded-md border border-red-200 px-2.5 py-1.5 text-red-700 hover:bg-red-50"
                            type="button"
                            onClick={() => void handleDeleteRule(rule.id)}
                            title="Удалить"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!detail?.rules.length ? (
                    <tr>
                      <td className="px-4 py-8 text-center text-slate-500" colSpan={5}>
                        Правила не настроены
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <aside className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                {editingRuleId ? 'Редактирование' : 'Новое правило'}
              </h2>
              {editingRuleId ? (
                <button className="rounded p-1 text-slate-500 hover:bg-slate-100" type="button" onClick={startCreateRule}>
                  <X className="h-4 w-4" />
                </button>
              ) : null}
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Название</span>
                <input
                  className="input-field"
                  value={ruleForm.name}
                  onChange={(event) => setRuleForm({ ...ruleForm, name: event.target.value })}
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Опросник</span>
                <select
                  className="input-field"
                  value={ruleForm.survey_config_id || ''}
                  onChange={(event) =>
                    setRuleForm({ ...ruleForm, survey_config_id: Number(event.target.value) })
                  }
                >
                  <option value="" disabled>
                    Выберите опросник
                  </option>
                  {surveys.map((survey) => (
                    <option key={survey.id} value={survey.id}>
                      {survey.name}
                    </option>
                  ))}
                </select>
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-700">Логика</span>
                  <select
                    className="input-field"
                    value={ruleForm.condition_logic}
                    onChange={(event) =>
                      setRuleForm({
                        ...ruleForm,
                        condition_logic: event.target.value as RoutingConditionLogic,
                      })
                    }
                  >
                    <option value="AND">AND</option>
                    <option value="OR">OR</option>
                  </select>
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-700">Приоритет</span>
                  <input
                    className="input-field"
                    type="number"
                    value={ruleForm.priority ?? ''}
                    onChange={(event) =>
                      setRuleForm({
                        ...ruleForm,
                        priority: event.target.value ? Number(event.target.value) : null,
                      })
                    }
                  />
                </label>
              </div>

              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input
                  className="h-5 w-5 rounded border-slate-300 text-teal-600"
                  type="checkbox"
                  checked={ruleForm.is_active}
                  onChange={(event) => setRuleForm({ ...ruleForm, is_active: event.target.checked })}
                />
                Активно
              </label>

              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-slate-800">Условия</div>
                <button
                  className="rounded-md border border-slate-200 px-3 py-1.5 text-sm hover:bg-slate-50"
                  type="button"
                  onClick={() => setAdvancedMode((value) => !value)}
                >
                  Расширенный режим
                </button>
              </div>

              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
                <input
                  className="input-field pl-9"
                  value={fieldSearch}
                  onChange={(event) => {
                    setFieldSearch(event.target.value)
                    void loadCrmFields(event.target.value)
                  }}
                  placeholder="Поиск CRM-поля"
                />
              </div>

              <div className="space-y-3">
                {ruleForm.conditions.map((condition, index) => {
                  const field = fieldsById.get(condition.crm_field_id)
                  const isValueDisabled =
                    condition.operator === 'is_filled' || condition.operator === 'is_empty'
                  const options = optionsByField[condition.crm_field_id] || []

                  return (
                    <div key={index} className="rounded-lg border border-slate-200 p-3">
                      <div className="mb-3 flex items-center justify-between">
                        <span className="text-sm font-medium text-slate-700">Условие {index + 1}</span>
                        <button
                          className="rounded p-1 text-red-600 hover:bg-red-50"
                          type="button"
                          onClick={() => removeCondition(index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>

                      <div className="space-y-3">
                        {advancedMode ? (
                          <input
                            className="input-field"
                            value={condition.crm_field_id}
                            onChange={(event) => updateCondition(index, { crm_field_id: event.target.value })}
                            placeholder="UF_CRM_..."
                          />
                        ) : (
                          <select
                            className="input-field"
                            value={condition.crm_field_id}
                            onChange={(event) => updateCondition(index, { crm_field_id: event.target.value })}
                          >
                            <option value="">CRM-поле</option>
                            {crmFields.map((crmField) => (
                              <option key={crmField.field_id} value={crmField.field_id}>
                                {formatCrmFieldTitle(crmField)}
                              </option>
                            ))}
                          </select>
                        )}

                        <select
                          className="input-field"
                          value={condition.operator}
                          onChange={(event) =>
                            updateCondition(index, {
                              operator: event.target.value as RoutingOperator,
                            })
                          }
                        >
                          {OPERATORS.map((operator) => (
                            <option key={operator} value={operator}>
                              {OPERATOR_LABELS[operator]}
                            </option>
                          ))}
                        </select>

                        {field?.is_list && !isValueDisabled ? (
                          <select
                            className="input-field"
                            value={String(condition.value ?? '')}
                            onChange={(event) => updateCondition(index, { value: event.target.value })}
                          >
                            <option value="">Значение</option>
                            {options.map((option) => (
                              <option key={option.option_id} value={option.option_id}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            className="input-field"
                            value={String(condition.value ?? '')}
                            disabled={isValueDisabled}
                            onChange={(event) => updateCondition(index, { value: event.target.value })}
                            placeholder={isValueDisabled ? 'Значение не требуется' : 'Значение'}
                          />
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>

              <button
                className="btn-secondary w-full rounded-lg px-4 py-2"
                type="button"
                onClick={() =>
                  setRuleForm((current) => ({
                    ...current,
                    conditions: [...current.conditions, emptyCondition()],
                  }))
                }
              >
                Добавить условие
              </button>

              <button
                className="btn-primary inline-flex w-full items-center justify-center gap-2 rounded-lg px-4 py-3"
                type="button"
                disabled={isSaving || !ruleForm.name.trim() || !ruleForm.survey_config_id}
                onClick={handleSaveRule}
              >
                <Save className="h-4 w-4" />
                Сохранить правило
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-4 flex items-center gap-2">
              <FlaskConical className="h-5 w-5 text-teal-700" />
              <h2 className="text-lg font-semibold">Проверить на сделке</h2>
            </div>
            <div className="space-y-3">
              <input
                className="input-field"
                type="number"
                value={dealId}
                onChange={(event) => setDealId(event.target.value)}
                placeholder="ID сделки Bitrix24"
              />
              <button
                className="btn-primary w-full rounded-lg px-4 py-3"
                type="button"
                disabled={isTesting || !dealId.trim()}
                onClick={handleTestDeal}
              >
                {isTesting ? 'Проверка...' : 'Проверить'}
              </button>
              {testResult ? (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                  <div className="font-semibold text-slate-900">
                    {testResult.selected_survey_name || 'Опросник не выбран'}
                  </div>
                  <div className="mt-1 text-slate-600">{testResult.reason}</div>
                  <div className="mt-2 text-xs text-slate-500">
                    {testResult.fallback_used ? 'Fallback' : `Правило #${testResult.selected_rule_id}`}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}
