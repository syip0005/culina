import { useState, useEffect } from 'react'
import { useDebounce } from '../utils/debounce.ts'
import { searchEntries, addMealItem, createMeal } from '../api.ts'
import { NutritionSummary } from './NutritionSummary.tsx'
import { LookupView } from './LookupView.tsx'
import type { Meal, MealType, NutritionEntry } from '../types.ts'

interface Props {
  mealType: MealType
  meal: Meal | null
  onClose: () => void
  onItemAdded: () => void
}

export function AddItemPanel({ mealType, meal: initialMeal, onClose, onItemAdded }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<NutritionEntry[]>([])
  const [searching, setSearching] = useState(false)
  const [meal, setMeal] = useState<Meal | null>(initialMeal)
  const [showLookup, setShowLookup] = useState(false)
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set())

  const debouncedQuery = useDebounce(query, 300)

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([])
      return
    }

    let cancelled = false
    setSearching(true)

    Promise.all([
      searchEntries(debouncedQuery, 'keyword', 5),
      searchEntries(debouncedQuery, 'semantic', 8),
    ]).then(([keyword, semantic]) => {
      if (cancelled) return
      const keywordIds = new Set(keyword.map((e) => e.id))
      const deduped = semantic.filter((e) => !keywordIds.has(e.id)).slice(0, 3)
      setResults([...keyword, ...deduped])
      setSearching(false)
    }).catch(() => {
      if (!cancelled) setSearching(false)
    })

    return () => { cancelled = true }
  }, [debouncedQuery])

  const ensureMeal = async (): Promise<Meal> => {
    if (meal) return meal
    const created = await createMeal({
      meal_type: mealType,
      eaten_at: new Date().toISOString(),
    })
    setMeal(created)
    return created
  }

  const handleAddResult = async (entry: NutritionEntry) => {
    const m = await ensureMeal()
    await addMealItem(m.id, { nutrition_entry_id: entry.id, quantity: 1.0 })
    setAddedIds((prev) => new Set(prev).add(entry.id))
    onItemAdded()
  }

  return (
    <div className="overlay">
      <div className="overlay-inner">
        <div className="overlay-header">
          <h2>Add to {mealType}</h2>
          <button className="secondary" onClick={onClose} style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
            Close
          </button>
        </div>

        <div style={{ marginBottom: '0.75rem', flexShrink: 0 }}>
          <input
            type="text"
            placeholder="Search foods..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button
            className="secondary"
            onClick={() => setShowLookup(true)}
            style={{ width: '100%', marginTop: '0.5rem', fontSize: '0.75rem' }}
          >
            Find New Items
          </button>
        </div>

        <div className="overlay-body">
          {searching && <div className="text-muted text-sm">Searching...</div>}

          {results.map((entry) => {
            const isAdded = addedIds.has(entry.id)
            return (
              <div
                key={entry.id}
                className={`search-result ${isAdded ? 'added' : ''}`}
                onClick={() => !isAdded && handleAddResult(entry)}
                style={{ cursor: isAdded ? 'default' : 'pointer' }}
              >
                <div className="search-result-name">
                  {entry.food_item}
                  {isAdded && <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem' }}>ADDED</span>}
                </div>
                {entry.brand && <div className="search-result-brand">{entry.brand}</div>}
                <div className="search-result-serving">
                  {entry.serving_amount}{entry.serving_unit}
                  {entry.serving_description && ` (${entry.serving_description})`}
                </div>
                <div className="search-result-macros">
                  <NutritionSummary
                    energyKj={entry.energy_kj}
                    proteinG={entry.protein_g}
                    fatG={entry.fat_g}
                    carbsG={entry.carbs_g}
                  />
                </div>
              </div>
            )
          })}

          {!searching && debouncedQuery && results.length === 0 && (
            <div className="text-muted text-sm mt-1">
              No results. Try "Find New Items" to search with AI.
            </div>
          )}
        </div>
      </div>

      {showLookup && (
        <LookupView
          initialQuery={query}
          mealType={mealType}
          mealId={meal?.id ?? null}
          onMealCreated={(m) => setMeal(m)}
          onItemAdded={onItemAdded}
          onBack={() => setShowLookup(false)}
        />
      )}
    </div>
  )
}
