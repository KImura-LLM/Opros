export interface RoutingClinicItem {
  key: string
  title: string
  default_survey_config_id?: number | null
  default_survey_name?: string | null
  is_enabled: boolean
}

export interface RoutingClinicsResponse {
  items: RoutingClinicItem[]
}

export type RoutingConditionLogic = 'AND' | 'OR'

export type RoutingOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'is_filled'
  | 'is_empty'

export interface RoutingCondition {
  id?: number | null
  crm_field_id: string
  operator: RoutingOperator
  value?: unknown
}

export interface RoutingRule {
  id: number
  clinic_key: string
  name: string
  is_active: boolean
  survey_config_id: number
  survey_name?: string | null
  condition_logic: RoutingConditionLogic
  priority: number
  conditions: RoutingCondition[]
  created_at?: string | null
  updated_at?: string | null
}

export interface RoutingClinicDetailResponse {
  clinic: RoutingClinicItem
  rules: RoutingRule[]
}

export interface RoutingRulePayload {
  name: string
  is_active: boolean
  survey_config_id: number
  condition_logic: RoutingConditionLogic
  priority?: number | null
  conditions: RoutingCondition[]
}

export interface CrmFieldItem {
  field_id: string
  title: string
  type?: string | null
  is_list: boolean
  is_active: boolean
  synced_at?: string | null
}

export interface CrmFieldsResponse {
  items: CrmFieldItem[]
}

export interface CrmFieldOptionItem {
  option_id: string
  label: string
  sort?: number | null
  is_active: boolean
}

export interface CrmFieldOptionsResponse {
  items: CrmFieldOptionItem[]
}

export interface RoutingSurveyListItem {
  id: number
  name: string
  version: string
  description?: string | null
  is_active: boolean
  nodes_count: number
  created_at: string
  updated_at?: string | null
}

export interface RoutingTestDealResponse {
  success: boolean
  clinic_key: string
  deal_id: number
  selected_survey_config_id?: number | null
  selected_survey_name?: string | null
  selected_rule_id?: number | null
  selected_rule_name?: string | null
  fallback_used: boolean
  reason: string
}
