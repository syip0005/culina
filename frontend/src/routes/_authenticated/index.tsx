import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '../../auth.tsx'
import { getDailySummary, listMeals, getEntry } from '../../api.ts'
import { todayRange, todayDateStr } from '../../utils/date.ts'
import { MealSection } from '../../components/MealSection.tsx'
import { AddItemPanel } from '../../components/AddItemPanel.tsx'
import type { Meal, MealType, NutritionEntry, DailySummaryResponse } from '../../types.ts'

export const Route = createFileRoute('/_authenticated/')({
  component: HomePage,
})

const MEAL_TYPES: MealType[] = ['breakfast', 'lunch', 'dinner', 'snacks']

function HomePage() {
  const { user } = useAuth()
  const tz = user?.settings?.timezone ?? 'Australia/Sydney'

  const [summary, setSummary] = useState<DailySummaryResponse | null>(null)
  const [mealsByType, setMealsByType] = useState<Record<MealType, Meal | null>>({
    breakfast: null, lunch: null, dinner: null, snacks: null,
  })
  const [entries, setEntries] = useState<Map<string, NutritionEntry>>(new Map())
  const [addingFor, setAddingFor] = useState<MealType | null>(null)
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(async () => {
    const dateStr = todayDateStr(tz)
    const { start, end } = todayRange(tz)

    const [summaryData, mealsData] = await Promise.all([
      getDailySummary(dateStr),
      listMeals({ eaten_after: start, eaten_before: end }),
    ])

    setSummary(summaryData)

    const byType: Record<MealType, Meal | null> = {
      breakfast: null, lunch: null, dinner: null, snacks: null,
    }
    for (const meal of mealsData) {
      if (meal.meal_type && meal.meal_type in byType) {
        byType[meal.meal_type as MealType] = meal
      }
    }
    setMealsByType(byType)

    // Collect unique entry IDs and fetch missing ones
    const entryIds = new Set<string>()
    for (const meal of mealsData) {
      for (const item of meal.items) {
        entryIds.add(item.nutrition_entry_id)
      }
    }

    setEntries((prev) => {
      const toFetch = [...entryIds].filter((id) => !prev.has(id))
      if (toFetch.length === 0) return prev
      // Kick off fetches and merge when done
      Promise.all(toFetch.map((id) => getEntry(id))).then((fetched) => {
        setEntries((current) => {
          const merged = new Map(current)
          for (const entry of fetched) {
            merged.set(entry.id, entry)
          }
          return merged
        })
      })
      return prev
    })
    setLoading(false)
  }, [tz])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (loading) return <div className="container">LOADING...</div>

  return (
    <div className="container">
      <div className="header">
        <h1>Culina</h1>
        <Link to="/settings">Settings</Link>
      </div>

      {summary && (
        <div className="summary-bar">
          <div className="summary-item">
            <div className="value">{Math.round(summary.consumed.energy_kj)}</div>
            <div className="label">Energy kJ</div>
          </div>
          <div className="summary-item">
            <div className="value">{Math.round(summary.consumed.protein_g)}</div>
            <div className="label">Protein g</div>
          </div>
          <div className="summary-item">
            <div className="value">{Math.round(summary.consumed.fat_g)}</div>
            <div className="label">Fat g</div>
          </div>
          <div className="summary-item">
            <div className="value">{Math.round(summary.consumed.carbs_g)}</div>
            <div className="label">Carbs g</div>
          </div>
        </div>
      )}

      {summary && (
        <div style={{ fontSize: '0.75rem', color: 'var(--color-muted)', marginBottom: '1rem', textAlign: 'center' }}>
          Remaining: {Math.round(summary.remaining.energy_kj)} kJ | {Math.round(summary.remaining.protein_g)}p | {Math.round(summary.remaining.fat_g)}f | {Math.round(summary.remaining.carbs_g)}c
        </div>
      )}

      {MEAL_TYPES.map((mt) => (
        <MealSection
          key={mt}
          mealType={mt}
          meal={mealsByType[mt]}
          entries={entries}
          onAddItem={() => setAddingFor(mt)}
          onRefresh={loadData}
        />
      ))}

      {addingFor && (
        <AddItemPanel
          mealType={addingFor}
          meal={mealsByType[addingFor]}
          onClose={() => setAddingFor(null)}
          onItemAdded={loadData}
        />
      )}
    </div>
  )
}
