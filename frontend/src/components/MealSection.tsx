import { useState } from 'react'
import type { Meal, MealType, NutritionEntry } from '../types.ts'
import { NutritionSummary } from './NutritionSummary.tsx'
import { deleteMealItem } from '../api.ts'

interface Props {
  mealType: MealType
  meal: Meal | null
  entries: Map<string, NutritionEntry>
  onAddItem: () => void
  onRefresh: () => void
}

const LABELS: Record<MealType, string> = {
  breakfast: 'BREAKFAST',
  lunch: 'LUNCH',
  dinner: 'DINNER',
  snacks: 'SNACKS',
}

export function MealSection({ mealType, meal, entries, onAddItem, onRefresh }: Props) {
  const [removedIds, setRemovedIds] = useState<Set<string>>(new Set())
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
    // Optimistically remove from UI immediately
    setRemovedIds((prev) => new Set(prev).add(itemId))
    await deleteMealItem(meal.id, itemId)
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
          />
        )}
      </div>

      {items.map((item) => {
        const entry = entries.get(item.nutrition_entry_id)
        return (
          <div key={item.id} className="meal-item">
            <span className="meal-item-name">
              {entry?.food_item ?? '...'}
              {item.quantity !== 1 && ` x${item.quantity}`}
            </span>
            {entry && (
              <span className="meal-item-macros">
                {Math.round(entry.energy_kj * item.quantity)} kJ
              </span>
            )}
            <button className="btn-delete" onClick={() => handleDelete(item.id)}>&times;</button>
          </div>
        )
      })}

      <div className="meal-section-footer">
        <button className="secondary" onClick={onAddItem} style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
          + ADD ITEM
        </button>
      </div>
    </div>
  )
}
