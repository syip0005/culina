import { supabase } from './supabase.ts'
import type {
  User,
  UserSettings,
  Meal,
  NutritionEntry,
  LookupResponse,
  DailySummaryResponse,
  PeriodStatsResponse,
} from './types.ts'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

async function getToken(): Promise<string> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) throw new Error('Not authenticated')
  return token
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const token = await getToken()
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function getMe() {
  return request<User>('GET', '/auth/me')
}

export function getSettings() {
  return request<UserSettings>('GET', '/users/me/settings')
}

export function updateSettings(data: Partial<UserSettings>) {
  return request<UserSettings>('PATCH', '/users/me/settings', data)
}

export function listMeals(params: { eaten_after?: string; eaten_before?: string; meal_type?: string }) {
  const qs = new URLSearchParams()
  if (params.eaten_after) qs.set('eaten_after', params.eaten_after)
  if (params.eaten_before) qs.set('eaten_before', params.eaten_before)
  if (params.meal_type) qs.set('meal_type', params.meal_type)
  return request<Meal[]>('GET', `/meals/?${qs}`)
}

export function createMeal(data: { meal_type?: string; eaten_at: string; items?: { nutrition_entry_id: string; quantity: number }[] }) {
  return request<Meal>('POST', '/meals/', data)
}

export function addMealItem(mealId: string, data: { nutrition_entry_id: string; quantity: number }) {
  return request<{ id: string }>('POST', `/meals/${mealId}/items`, data)
}

export function deleteMealItem(mealId: string, itemId: string) {
  return request<void>('DELETE', `/meals/${mealId}/items/${itemId}`)
}

export function searchEntries(query: string, mode: 'keyword' | 'semantic', limit: number) {
  return request<NutritionEntry[]>('POST', '/nutrition-entries/search', { query, mode, limit })
}

export function createNutritionEntry(data: {
  food_item: string
  brand?: string
  source_url?: string
  serving_amount: number
  serving_unit: string
  serving_description?: string | null
  energy_kj: number
  protein_g: number
  fat_g: number
  carbs_g: number
  source: string
  notes?: string | null
}) {
  return request<NutritionEntry>('POST', '/nutrition-entries/', data)
}

export function getEntry(id: string) {
  return request<NutritionEntry>('GET', `/nutrition-entries/${id}`)
}

export function deleteNutritionEntry(id: string) {
  return request<void>('DELETE', `/nutrition-entries/${id}`)
}

export function lookup(data: { text: string; conversation_id?: string }) {
  return request<LookupResponse>('POST', '/lookup/', data)
}

export function getDailySummary(date?: string) {
  const qs = date ? `?date=${date}` : ''
  return request<DailySummaryResponse>('GET', `/summary/daily${qs}`)
}

export function getPeriodStats(period: string, date?: string) {
  const qs = new URLSearchParams({ period })
  if (date) qs.set('date', date)
  return request<PeriodStatsResponse>('GET', `/summary/stats?${qs}`)
}

export function getSuggestions(mealType: string, limit = 10) {
  const qs = new URLSearchParams({ meal_type: mealType, limit: String(limit) })
  return request<NutritionEntry[]>('GET', `/suggestions/?${qs}`)
}
