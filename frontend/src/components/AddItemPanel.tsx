import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../auth.tsx'
import { useDebounce } from '../utils/debounce.ts'
import { searchEntries, addMealItem, createMeal, deleteNutritionEntry } from '../api.ts'
import { dateMidpointISO } from '../utils/date.ts'
import { NutritionSummary } from './NutritionSummary.tsx'
import { LookupView } from './LookupView.tsx'
import type { Meal, MealType, NutritionEntry, ServingUnit } from '../types.ts'

interface Props {
  mealType: MealType
  meal: Meal | null
  /** YYYY-MM-DD + timezone so we create meals on the correct day */
  targetDate: string
  timezone: string
  suggestions?: NutritionEntry[]
  onClose: () => void
  onItemAdded: () => void
  onOptimisticAdd?: (entry: NutritionEntry, quantity: number) => void
}

/** Units where the user adjusts a weight/volume amount */
function isScalableUnit(unit: ServingUnit): boolean {
  return unit === 'g' || unit === 'ml'
}

function servingLabel(amount: number, unit: ServingUnit, description: string | null): string {
  if (isScalableUnit(unit)) {
    return `${amount}${unit}${description ? ` (${description})` : ''}`
  }
  // piece / serve — show description if available, otherwise "1 piece" etc.
  if (description) return description
  return `${amount} ${unit}${amount !== 1 ? 's' : ''}`
}

export function AddItemPanel({ mealType, meal: initialMeal, targetDate, timezone, suggestions = [], onClose, onItemAdded, onOptimisticAdd }: Props) {
  const { user } = useAuth()
  const eUnit = user?.settings?.preferred_energy_unit ?? 'kj'
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<NutritionEntry[]>([])
  const [searching, setSearching] = useState(false)
  const [meal, setMeal] = useState<Meal | null>(initialMeal)
  const [showLookup, setShowLookup] = useState(false)
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set())
  const [adding, setAdding] = useState<{ entry: NutritionEntry; value: string } | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [expandedInfoId, setExpandedInfoId] = useState<string | null>(null)
  const popupRef = useRef<HTMLDivElement>(null)

  // Close info popup on click outside
  useEffect(() => {
    if (!expandedInfoId) return
    const handleClick = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        setExpandedInfoId(null)
      }
    }
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [expandedInfoId])

  const debouncedQuery = useDebounce(query, 300)

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([])
      setSearching(false)
      return
    }

    let cancelled = false
    setSearching(true)

    // Fire keyword search first (faster), then merge semantic results
    searchEntries(debouncedQuery, 'keyword', 5).then((keyword) => {
      if (cancelled) return
      setResults(keyword)

      searchEntries(debouncedQuery, 'semantic', 8).then((semantic) => {
        if (cancelled) return
        const keywordIds = new Set(keyword.map((e) => e.id))
        const deduped = semantic.filter((e) => !keywordIds.has(e.id)).slice(0, 3)
        setResults([...keyword, ...deduped])
        setSearching(false)
      }).catch(() => {
        if (!cancelled) setSearching(false)
      })
    }).catch(() => {
      if (!cancelled) setSearching(false)
    })

    return () => { cancelled = true }
  }, [debouncedQuery])

  const ensureMeal = async (): Promise<Meal> => {
    if (meal) return meal
    const created = await createMeal({
      meal_type: mealType,
      eaten_at: dateMidpointISO(targetDate, timezone),
    })
    setMeal(created)
    return created
  }

  const handleDelete = async (entry: NutritionEntry) => {
    setDeleteError(null)
    try {
      await deleteNutritionEntry(entry.id)
      setResults((prev) => prev.filter((e) => e.id !== entry.id))
      setDeletingId(null)
    } catch {
      setDeleteError(entry.id)
      setDeletingId(null)
    }
  }

  const handleSelect = (entry: NutritionEntry) => {
    if (addedIds.has(entry.id)) return
    const defaultValue = isScalableUnit(entry.serving_unit)
      ? String(entry.serving_amount)
      : '1'
    setAdding({ entry, value: defaultValue })
  }

  const confirmAdd = async () => {
    if (!adding) return
    const { entry, value } = adding
    const num = parseFloat(value) || 1

    // For g/ml: quantity = userAmount / baseServingAmount
    // For piece/serve: quantity = userValue directly
    const quantity = isScalableUnit(entry.serving_unit)
      ? num / entry.serving_amount
      : num

    // Optimistically update UI immediately
    setAddedIds((prev) => new Set(prev).add(entry.id))
    setAdding(null)
    if (onOptimisticAdd) onOptimisticAdd(entry, quantity)

    const m = await ensureMeal()
    await addMealItem(m.id, { nutrition_entry_id: entry.id, quantity })
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
          {searching && results.length === 0 && <div className="text-muted text-sm">Searching...</div>}

          {(debouncedQuery.trim() ? results : suggestions).map((entry) => {
            const isAdded = addedIds.has(entry.id)
            const isAddingThis = adding?.entry.id === entry.id
            const scalable = isScalableUnit(entry.serving_unit)
            const isOwned = entry.user_id === user?.id
            const isConfirmingDelete = deletingId === entry.id

            return (
              <div
                key={entry.id}
                className={`search-result ${isAdded ? 'added' : ''} ${isOwned && !isAdded ? 'search-result-owned' : ''}`}
                onClick={() => !isAdded && !isAddingThis && handleSelect(entry)}
                style={{ cursor: isAdded || isAddingThis ? 'default' : 'pointer' }}
              >
                <div className="search-result-top">
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="search-result-name">
                      {entry.food_item}
                      {isAdded && <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem' }}>ADDED</span>}
                    </div>
                  </div>
                  <span className="search-result-actions">
                    <button
                      className="btn-info"
                      onClick={(e) => {
                        e.stopPropagation()
                        setExpandedInfoId(expandedInfoId === entry.id ? null : entry.id)
                      }}
                      title="Entry details"
                    >
                      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <circle cx="8" cy="8" r="7" />
                        <line x1="8" y1="7" x2="8" y2="12" />
                        <circle cx="8" cy="4.5" r="0.5" fill="currentColor" stroke="none" />
                      </svg>
                    </button>
                    {isOwned && !isAdded && (
                      <button
                        className="btn-delete-entry"
                        onClick={(e) => { e.stopPropagation(); setDeleteError(null); setDeletingId(isConfirmingDelete ? null : entry.id) }}
                        title="Delete entry"
                      >
                        ×
                      </button>
                    )}
                  </span>
                </div>
                {expandedInfoId === entry.id && (
                  <div className="entry-info-popup" ref={popupRef} onClick={(e) => e.stopPropagation()}>
                    <div><strong>Source:</strong> {entry.source}</div>
                    <div><strong>Added:</strong> {new Date(entry.date_retrieved).toLocaleDateString()}</div>
                    {entry.brand && <div><strong>Brand:</strong> {entry.brand}</div>}
                    <div><strong>Serving:</strong> {servingLabel(entry.serving_amount, entry.serving_unit, entry.serving_description)}</div>
                    {entry.notes && <div><strong>Notes:</strong> {entry.notes}</div>}
                    {entry.source_url && <div><a href={entry.source_url} target="_blank" rel="noopener noreferrer">Source link ↗</a></div>}
                  </div>
                )}
                {isConfirmingDelete && (
                  <div className="delete-confirm" onClick={(e) => e.stopPropagation()}>
                    <span className="text-xs">Delete this entry?</span>
                    <button onClick={() => handleDelete(entry)} style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}>
                      Yes
                    </button>
                    <button className="secondary" onClick={() => setDeletingId(null)} style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}>
                      No
                    </button>
                  </div>
                )}
                {deleteError === entry.id && (
                  <div className="delete-error text-xs" onClick={(e) => e.stopPropagation()}>
                    Can't delete — used in a meal
                  </div>
                )}
                {entry.brand && <div className="search-result-brand">{entry.brand}</div>}
                <div className="search-result-serving">
                  {servingLabel(entry.serving_amount, entry.serving_unit, entry.serving_description)}
                </div>
                <div className="search-result-macros">
                  <NutritionSummary
                    energyKj={entry.energy_kj}
                    proteinG={entry.protein_g}
                    fatG={entry.fat_g}
                    carbsG={entry.carbs_g}
                    energyUnit={eUnit}
                  />
                </div>

                {isAddingThis && (
                  <div className="quantity-inline" onClick={(e) => e.stopPropagation()}>
                    <label style={{ fontSize: '0.7rem', marginRight: '0.3rem' }}>
                      {scalable ? entry.serving_unit : (entry.serving_description || `${entry.serving_amount} ${entry.serving_unit}`)}:
                    </label>
                    <input
                      type="number"
                      value={adding.value}
                      onChange={(e) => setAdding({ ...adding, value: e.target.value })}
                      step={scalable ? '1' : '0.5'}
                      min={scalable ? '1' : '0.5'}
                      autoFocus
                    />
                    <button onClick={confirmAdd} style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}>
                      Add
                    </button>
                    <button
                      className="secondary"
                      onClick={() => setAdding(null)}
                      style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                    >
                      Cancel
                    </button>
                  </div>
                )}
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
          targetDate={targetDate}
          timezone={timezone}
          onMealCreated={(m) => setMeal(m)}
          onItemAdded={onItemAdded}
          onBack={() => setShowLookup(false)}
        />
      )}
    </div>
  )
}
