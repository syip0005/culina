import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useAuth } from '../../auth.tsx'
import { getDailySummary, listMeals, getEntry } from '../../api.ts'
import { dateRange, todayDateStr, shiftDate, formatDateLabel } from '../../utils/date.ts'
import { MealSection } from '../../components/MealSection.tsx'
import { AddItemPanel } from '../../components/AddItemPanel.tsx'
import { displayEnergy, energyLabel } from '../../utils/energy.ts'
import type { Meal, MealItem, MealType, NutritionEntry, DailySummaryResponse } from '../../types.ts'

export const Route = createFileRoute('/_authenticated/')({
  component: HomePage,
})

const MEAL_TYPES: MealType[] = ['breakfast', 'lunch', 'dinner', 'snacks']

function currentMealType(tz: string): MealType {
  const hour = parseInt(new Intl.DateTimeFormat('en-US', { timeZone: tz, hour: 'numeric', hour12: false }).format(new Date()), 10)
  if (hour >= 5 && hour < 10) return 'breakfast'
  if (hour >= 10 && hour < 14) return 'lunch'
  if (hour >= 14 && hour < 20) return 'dinner'
  return 'snacks'
}

interface DayData {
  summary: DailySummaryResponse | null
  mealsByType: Record<MealType, Meal | null>
}

function HomePage() {
  const { user } = useAuth()
  const tz = user?.settings?.timezone ?? 'Australia/Sydney'
  const eUnit = user?.settings?.preferred_energy_unit ?? 'kj'
  const today = todayDateStr(tz)

  const [currentDate, setCurrentDate] = useState(today)
  const [summary, setSummary] = useState<DailySummaryResponse | null>(null)
  const [mealsByType, setMealsByType] = useState<Record<MealType, Meal | null>>({
    breakfast: null, lunch: null, dinner: null, snacks: null,
  })
  const [entries, setEntries] = useState<Map<string, NutritionEntry>>(new Map())
  const [addingFor, setAddingFor] = useState<MealType | null>(null)
  const [loading, setLoading] = useState(true)
  const [sliding, setSliding] = useState<'left' | 'right' | null>(null)

  // Cache for preloaded days
  const cache = useRef<Map<string, DayData>>(new Map())

  const fetchDay = useCallback(async (dateStr: string): Promise<DayData> => {
    const { start, end } = dateRange(dateStr, tz)
    const [summaryData, mealsData] = await Promise.all([
      getDailySummary(dateStr),
      listMeals({ eaten_after: start, eaten_before: end }),
    ])

    const byType: Record<MealType, Meal | null> = {
      breakfast: null, lunch: null, dinner: null, snacks: null,
    }
    for (const meal of mealsData) {
      if (meal.meal_type && meal.meal_type in byType) {
        byType[meal.meal_type as MealType] = meal
      }
    }

    return { summary: summaryData, mealsByType: byType }
  }, [tz])

  const fetchEntries = useCallback((mealsMap: Record<MealType, Meal | null>) => {
    const entryIds = new Set<string>()
    for (const meal of Object.values(mealsMap)) {
      if (!meal) continue
      for (const item of meal.items) {
        entryIds.add(item.nutrition_entry_id)
      }
    }
    setEntries((prev) => {
      const toFetch = [...entryIds].filter((id) => !prev.has(id))
      if (toFetch.length === 0) return prev
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
  }, [])

  const applyDay = useCallback((data: DayData) => {
    setSummary(data.summary)
    setMealsByType(data.mealsByType)
    fetchEntries(data.mealsByType)
    setLoading(false)
  }, [fetchEntries])

  // Preload adjacent days in background
  const preload = useCallback((dateStr: string) => {
    for (const offset of [-1, -2]) {
      const d = shiftDate(dateStr, offset)
      if (!cache.current.has(d)) {
        fetchDay(d).then((data) => cache.current.set(d, data))
      }
    }
  }, [fetchDay])

  const loadData = useCallback(async () => {
    const target = currentDate
    const cached = cache.current.get(target)
    if (cached) {
      applyDay(cached)
      // Refresh in background for today to keep data fresh
      if (target === today) {
        fetchDay(target).then((data) => {
          cache.current.set(target, data)
          applyDay(data)
        })
      }
    } else {
      const data = await fetchDay(target)
      cache.current.set(target, data)
      applyDay(data)
    }
    preload(target)
  }, [currentDate, today, fetchDay, applyDay, preload])

  useEffect(() => {
    loadData()
  }, [loadData])

  const navigate = useCallback((direction: -1 | 1) => {
    if (addingFor) return // don't navigate while adding items
    const next = shiftDate(currentDate, direction)
    // Invalidate cache for the day we're leaving if it's today (could be stale)
    if (currentDate === today) cache.current.delete(currentDate)
    setSliding(direction === -1 ? 'left' : 'right')
    setCurrentDate(next)
    // Clear slide animation after it plays
    setTimeout(() => setSliding(null), 200)
  }, [currentDate, today, addingFor])

  // Swipe navigation (mobile)
  const touchRef = useRef<{ x: number; y: number; t: number } | null>(null)
  useEffect(() => {
    const onStart = (e: TouchEvent) => {
      if (addingFor) return
      const touch = e.touches[0]
      touchRef.current = { x: touch.clientX, y: touch.clientY, t: Date.now() }
    }
    const onEnd = (e: TouchEvent) => {
      if (!touchRef.current || addingFor) return
      const touch = e.changedTouches[0]
      const dx = touch.clientX - touchRef.current.x
      const dy = touch.clientY - touchRef.current.y
      const dt = Date.now() - touchRef.current.t
      touchRef.current = null
      // Require: horizontal > 60px, more horizontal than vertical (ratio 2:1), under 400ms
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 2 && dt < 400) {
        navigate(dx < 0 ? 1 : -1)
      }
    }
    window.addEventListener('touchstart', onStart, { passive: true })
    window.addEventListener('touchend', onEnd, { passive: true })
    return () => {
      window.removeEventListener('touchstart', onStart)
      window.removeEventListener('touchend', onEnd)
    }
  }, [navigate, addingFor])

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (addingFor) return
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        navigate(-1)
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        navigate(1)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate, addingFor])

  const handleOptimisticDelete = useCallback((macros: { energy_kj: number; protein_g: number; fat_g: number; carbs_g: number }) => {
    cache.current.delete(currentDate)
    setSummary((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        consumed: {
          energy_kj: prev.consumed.energy_kj - macros.energy_kj,
          protein_g: prev.consumed.protein_g - macros.protein_g,
          fat_g: prev.consumed.fat_g - macros.fat_g,
          carbs_g: prev.consumed.carbs_g - macros.carbs_g,
        },
        remaining: {
          energy_kj: prev.remaining.energy_kj + macros.energy_kj,
          protein_g: prev.remaining.protein_g + macros.protein_g,
          fat_g: prev.remaining.fat_g + macros.fat_g,
          carbs_g: prev.remaining.carbs_g + macros.carbs_g,
        },
      }
    })
  }, [currentDate])

  const handleOptimisticAdd = useCallback((mealType: MealType, entry: NutritionEntry, quantity: number) => {
    cache.current.delete(currentDate)
    setSummary((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        consumed: {
          energy_kj: prev.consumed.energy_kj + entry.energy_kj * quantity,
          protein_g: prev.consumed.protein_g + entry.protein_g * quantity,
          fat_g: prev.consumed.fat_g + entry.fat_g * quantity,
          carbs_g: prev.consumed.carbs_g + entry.carbs_g * quantity,
        },
        remaining: {
          energy_kj: prev.remaining.energy_kj - entry.energy_kj * quantity,
          protein_g: prev.remaining.protein_g - entry.protein_g * quantity,
          fat_g: prev.remaining.fat_g - entry.fat_g * quantity,
          carbs_g: prev.remaining.carbs_g - entry.carbs_g * quantity,
        },
      }
    })

    setEntries((prev) => {
      if (prev.has(entry.id)) return prev
      const next = new Map(prev)
      next.set(entry.id, entry)
      return next
    })

    const tempItem: MealItem = {
      id: `temp-${Date.now()}`,
      meal_id: null,
      nutrition_entry_id: entry.id,
      quantity,
      notes: null,
      created_at: new Date().toISOString(),
    }
    setMealsByType((prev) => {
      const existing = prev[mealType]
      if (existing) {
        return { ...prev, [mealType]: { ...existing, items: [...existing.items, tempItem] } }
      }
      return {
        ...prev,
        [mealType]: {
          id: `temp-meal-${Date.now()}`,
          user_id: '',
          meal_type: mealType,
          name: null,
          eaten_at: new Date().toISOString(),
          notes: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          items: [tempItem],
        },
      }
    })
  }, [currentDate])

  if (loading) return <div className="container">LOADING...</div>

  const isToday = currentDate === today
  const dateLabel = formatDateLabel(currentDate, today)

  return (
    <div className="container">
      <div className="header">
        <h1>Culina</h1>
        <Link to="/settings">Settings</Link>
      </div>

      <div className="day-nav">
        <button className="day-nav-btn" onClick={() => navigate(-1)} aria-label="Previous day">&larr;</button>
        <div className="day-nav-label">
          <span className={`day-nav-text ${sliding === 'left' ? 'slide-left' : sliding === 'right' ? 'slide-right' : ''}`}>
            {dateLabel}
          </span>
          {!isToday && (
            <button className="day-nav-today" onClick={() => { setCurrentDate(today); setSliding(null) }}>
              Today
            </button>
          )}
        </div>
        <button className="day-nav-btn" onClick={() => navigate(1)} aria-label="Next day">&rarr;</button>
      </div>

      {summary && (
        <div className="summary-bar">
          <div className="summary-item">
            <div className="value">{displayEnergy(summary.consumed.energy_kj, eUnit)}</div>
            <div className="label">Energy {energyLabel(eUnit)}</div>
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
          Remaining: {displayEnergy(summary.remaining.energy_kj, eUnit)} {energyLabel(eUnit)} | {Math.round(summary.remaining.protein_g)}p | {Math.round(summary.remaining.fat_g)}f | {Math.round(summary.remaining.carbs_g)}c
        </div>
      )}

      {MEAL_TYPES.map((mt) => (
        <MealSection
          key={mt}
          mealType={mt}
          meal={mealsByType[mt]}
          entries={entries}
          energyUnit={eUnit}
          highlight={isToday && currentMealType(tz) === mt}
          onAddItem={() => setAddingFor(mt)}
          onRefresh={() => loadData()}
          onOptimisticDelete={handleOptimisticDelete}
        />
      ))}

      {addingFor && (
        <AddItemPanel
          mealType={addingFor}
          meal={mealsByType[addingFor]}
          onClose={() => setAddingFor(null)}
          onItemAdded={() => loadData()}
          onOptimisticAdd={(entry, quantity) => handleOptimisticAdd(addingFor, entry, quantity)}
        />
      )}
    </div>
  )
}
