export type NutritionSource = 'afcd' | 'search' | 'manual' | 'estimate'
export type ServingUnit = 'g' | 'ml' | 'piece' | 'serve'
export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snacks'

export interface User {
  id: string
  external_id: string
  email: string | null
  display_name: string | null
  created_at: string | null
  updated_at: string | null
  settings: UserSettings | null
}

export interface UserSettings {
  daily_energy_target_kj: number | null
  daily_protein_target_g: number | null
  daily_fat_target_g: number | null
  daily_carbs_target_g: number | null
  timezone: string
  preferred_energy_unit: string
  extra: Record<string, unknown>
}

export interface NutritionEntry {
  id: string
  user_id: string
  food_item: string
  brand: string
  source_url: string
  serving_amount: number
  serving_unit: ServingUnit
  serving_description: string | null
  energy_kj: number
  protein_g: number
  fat_g: number
  carbs_g: number
  source: NutritionSource
  notes: string | null
  date_retrieved: string
  afcd_food_key: string | null
  base_entry_id: string | null
  search_text: string
}

export interface MealItem {
  id: string
  meal_id: string | null
  nutrition_entry_id: string
  quantity: number
  notes: string | null
  created_at: string
}

export interface Meal {
  id: string
  user_id: string
  meal_type: string | null
  name: string | null
  eaten_at: string
  notes: string | null
  created_at: string
  updated_at: string
  items: MealItem[]
}

export interface SearchNutritionInfo {
  food_item: string
  brand: string
  source_url: string | null
  serving_amount: number
  serving_unit: ServingUnit
  serving_description: string | null
  energy_kj: number
  protein_g: number
  fat_g: number
  carbs_g: number
  is_estimate: boolean
  source: NutritionSource
  notes: string | null
}

export interface SearchNutritionNotFound {
  food_item: string
  reason: string
  suggestions: string[]
}

export interface FollowUpResponse {
  kind: 'follow_up'
  conversation_id: string
  follow_up_question: string
  follow_up_buttons: string[]
}

export interface SearchNutritionResult {
  items: (SearchNutritionInfo | SearchNutritionNotFound)[]
}

export interface NutritionResultResponse {
  kind: 'result'
  conversation_id: string
  result: SearchNutritionResult
}

export type LookupResponse = FollowUpResponse | NutritionResultResponse

export interface Macros {
  energy_kj: number
  protein_g: number
  fat_g: number
  carbs_g: number
}

export interface DailySummaryResponse {
  date: string
  consumed: Macros
  targets: Macros
  remaining: Macros
}

export interface DayStats {
  date: string
  consumed: Macros
  targets: Macros
  on_target: boolean
}

export interface PeriodStatsResponse {
  period: string
  start_date: string
  end_date: string
  days_in_period: number
  days_logged: number
  days_on_target: number
  average_consumed: Macros
  daily: DayStats[]
}

export type GoalMode = 'under' | 'over' | 'within'
export type EnergyUnit = 'kj' | 'kcal'

export function isSearchNutritionInfo(
  item: SearchNutritionInfo | SearchNutritionNotFound,
): item is SearchNutritionInfo {
  return 'energy_kj' in item
}
