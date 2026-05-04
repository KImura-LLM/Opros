import type {
  CrmFieldOptionsResponse,
  CrmFieldsResponse,
  RoutingClinicDetailResponse,
  RoutingClinicItem,
  RoutingClinicsResponse,
  RoutingRule,
  RoutingRulePayload,
  RoutingSurveyListItem,
  RoutingTestDealResponse,
} from '@/types'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

async function fetchWithAdminAuth<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (response.status === 401) {
    document.cookie = `admin_redirect=${encodeURIComponent(window.location.pathname)}; path=/; SameSite=Lax; max-age=300`
    window.location.href = '/admin/login'
    throw new Error('Требуется вход администратора')
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP error ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function getRoutingClinics(): Promise<RoutingClinicsResponse> {
  return fetchWithAdminAuth<RoutingClinicsResponse>('/routing/clinics')
}

export function getRoutingClinic(clinicKey: string): Promise<RoutingClinicDetailResponse> {
  return fetchWithAdminAuth<RoutingClinicDetailResponse>(`/routing/clinics/${clinicKey}`)
}

export function saveRoutingClinicSettings(
  clinicKey: string,
  payload: { default_survey_config_id?: number | null; is_enabled: boolean }
): Promise<RoutingClinicItem> {
  return fetchWithAdminAuth<RoutingClinicItem>(`/routing/clinics/${clinicKey}/settings`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function createRoutingRule(
  clinicKey: string,
  payload: RoutingRulePayload
): Promise<RoutingRule> {
  return fetchWithAdminAuth<RoutingRule>(`/routing/clinics/${clinicKey}/rules`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateRoutingRule(
  ruleId: number,
  payload: RoutingRulePayload
): Promise<RoutingRule> {
  return fetchWithAdminAuth<RoutingRule>(`/routing/rules/${ruleId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteRoutingRule(ruleId: number): Promise<{ success: boolean }> {
  return fetchWithAdminAuth<{ success: boolean }>(`/routing/rules/${ruleId}`, {
    method: 'DELETE',
  })
}

export function reorderRoutingRules(
  clinicKey: string,
  items: Array<{ id: number; priority: number }>
): Promise<{ success: boolean }> {
  return fetchWithAdminAuth<{ success: boolean }>(
    `/routing/clinics/${clinicKey}/rules/reorder`,
    {
      method: 'POST',
      body: JSON.stringify({ items }),
    }
  )
}

export function getRoutingSurveys(): Promise<RoutingSurveyListItem[]> {
  return fetchWithAdminAuth<RoutingSurveyListItem[]>('/editor/surveys?active_only=true')
}

export function getCrmFields(search = ''): Promise<CrmFieldsResponse> {
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  params.set('active_only', 'true')
  return fetchWithAdminAuth<CrmFieldsResponse>(`/routing/crm-fields?${params.toString()}`)
}

export function getCrmFieldOptions(
  fieldId: string,
  search = ''
): Promise<CrmFieldOptionsResponse> {
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  params.set('active_only', 'true')
  return fetchWithAdminAuth<CrmFieldOptionsResponse>(
    `/routing/crm-fields/${encodeURIComponent(fieldId)}/options?${params.toString()}`
  )
}

export function syncCrmFields(): Promise<{
  success: boolean
  fields_updated: number
  options_updated: number
  synced_at: string
  message?: string
}> {
  return fetchWithAdminAuth('/routing/crm-fields/sync', {
    method: 'POST',
  })
}

export function testDealRouting(
  clinicKey: string,
  dealId: number
): Promise<RoutingTestDealResponse> {
  return fetchWithAdminAuth<RoutingTestDealResponse>(
    `/routing/clinics/${clinicKey}/test-deal`,
    {
      method: 'POST',
      body: JSON.stringify({ deal_id: dealId }),
    }
  )
}
