import { useState, useEffect } from 'react'
import type { Meal, MealType, NutritionEntry } from '../types.ts'
import { NutritionSummary } from './NutritionSummary.tsx'
import { displayEnergy, energyLabel } from '../utils/energy.ts'
import { deleteMealItem } from '../api.ts'

interface Props {
  mealType: MealType
  meal: Meal | null
  entries: Map<string, NutritionEntry>
  energyUnit?: string
  highlight?: boolean
  onAddItem: () => void
  onRefresh: () => void
  onOptimisticDelete?: (macros: { energy_kj: number; protein_g: number; fat_g: number; carbs_g: number }) => void
}

const LABELS: Record<MealType, string> = {
  breakfast: 'BREAKFAST',
  lunch: 'LUNCH',
  dinner: 'DINNER',
  snacks: 'SNACKS',
}

export function MealSection({ mealType, meal, entries, energyUnit = 'kj', highlight, onAddItem, onRefresh, onOptimisticDelete }: Props) {
  const [removedIds, setRemovedIds] = useState<Set<string>>(new Set())

  // Clear optimistic removals when fresh data arrives from the server
  const itemIds = meal?.items.map((i) => i.id).join(',') ?? ''
  useEffect(() => {
    setRemovedIds(new Set())
  }, [itemIds])

  const items = (meal?.items ?? []).filter((item) => !removedIds.has(item.id))

  let totalEnergy = 0
  let totalProtein = 0
  let totalFat = 0
  let totalCarbs = 0

  for (const item of items) {
    const entry = entries.get(item.nutrition_entry_id)
    if (entry) {
      totalEnergy += entry.energy_kj * item.quantity
      totalProtein += entry.protein_g * item.quantity
      totalFat += entry.fat_g * item.quantity
      totalCarbs += entry.carbs_g * item.quantity
    }
  }

  const handleDelete = async (itemId: string) => {
    if (!meal) return
    // Compute macros for the deleted item so we can optimistically update the summary
    const item = meal.items.find((i) => i.id === itemId)
    const entry = item ? entries.get(item.nutrition_entry_id) : undefined
    if (item && entry && onOptimisticDelete) {
      onOptimisticDelete({
        energy_kj: entry.energy_kj * item.quantity,
        protein_g: entry.protein_g * item.quantity,
        fat_g: entry.fat_g * item.quantity,
        carbs_g: entry.carbs_g * item.quantity,
      })
    }
    // Optimistically remove from UI immediately
    setRemovedIds((prev) => new Set(prev).add(itemId))
    try {
      await deleteMealItem(meal.id, itemId)
    } catch {
      // Delete failed — restore the item in the UI
      setRemovedIds((prev) => {
        const next = new Set(prev)
        next.delete(itemId)
        return next
      })
    }
    onRefresh()
  }

  return (
    <div className="meal-section">
      <div className="meal-section-header">
        <h2>{LABELS[mealType]}</h2>
        {items.length > 0 && (
          <NutritionSummary
            energyKj={totalEnergy}
            proteinG={totalProtein}
            fatG={totalFat}
            carbsG={totalCarbs}
            energyUnit={energyUnit}
          />
        )}
      </div>

      {items.map((item) => {
        const entry = entries.get(item.nutrition_entry_id)
        return (
          <div key={item.id} className="meal-item">
            <span className="meal-item-name">
              {entry?.food_item ?? '...'}
              {item.quantity !== 1 && entry && (entry.serving_unit === 'g' || entry.serving_unit === 'ml')
                ? ` ${Math.round(entry.serving_amount * item.quantity)}${entry.serving_unit}`
                : item.quantity !== 1 && ` x${item.quantity}`}
            </span>
            {entry && (
              <span className="meal-item-macros">
                {displayEnergy(entry.energy_kj * item.quantity, energyUnit)} {energyLabel(energyUnit)}
              </span>
            )}
            <button className="btn-delete" onClick={() => handleDelete(item.id)}>&times;</button>
          </div>
        )
      })}

      <div className="meal-section-footer">
        <button className={highlight ? 'secondary highlight-add' : 'secondary'} onClick={onAddItem} style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
          + ADD ITEM
        </button>
      </div>
    </div>
  )
}
