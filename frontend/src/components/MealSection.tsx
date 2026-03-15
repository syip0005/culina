import { useState, useEffect } from 'react'
import type { Meal, MealType, NutritionEntry } from '../types.ts'
import { NutritionSummary } from './NutritionSummary.tsx'
import { displayEnergy, energyLabel } from '../utils/energy.ts'
import { deleteMealItem, updateMealItem } from '../api.ts'

interface Props {
  mealType: MealType
  meal: Meal | null
  entries: Map<string, NutritionEntry>
  energyUnit?: string
  highlight?: boolean
  onAddItem: () => void
  onRefresh: () => void
  onOptimisticDelete?: (macros: { energy_kj: number; protein_g: number; fat_g: number; carbs_g: number }) => void
  onOptimisticUpdate?: (delta: { energy_kj: number; protein_g: number; fat_g: number; carbs_g: number }) => void
}

const LABELS: Record<MealType, string> = {
  breakfast: 'BREAKFAST',
  lunch: 'LUNCH',
  dinner: 'DINNER',
  snacks: 'SNACKS',
}

export function MealSection({ mealType, meal, entries, energyUnit = 'kj', highlight, onAddItem, onRefresh, onOptimisticDelete, onOptimisticUpdate }: Props) {
  const [removedIds, setRemovedIds] = useState<Set<string>>(new Set())
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState(false)

  // Clear optimistic removals and close editor when fresh data arrives from the server
  const itemIds = meal?.items.map((i) => i.id).join(',') ?? ''
  useEffect(() => {
    setRemovedIds(new Set())
    setEditingId(null)
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

  const startEdit = (itemId: string) => {
    const item = items.find((i) => i.id === itemId)
    if (!item) return
    const entry = entries.get(item.nutrition_entry_id)
    if (!entry) return
    const isWeight = entry.serving_unit === 'g' || entry.serving_unit === 'ml'
    const displayVal = isWeight
      ? String(Math.round(entry.serving_amount * item.quantity))
      : String(item.quantity)
    setEditingId(itemId)
    setEditValue(displayVal)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditValue('')
  }

  const handleSave = async () => {
    if (!meal || !editingId || saving) return
    const item = items.find((i) => i.id === editingId)
    if (!item) return
    const entry = entries.get(item.nutrition_entry_id)
    if (!entry) return

    const isWeight = entry.serving_unit === 'g' || entry.serving_unit === 'ml'
    const parsed = parseFloat(editValue)
    if (isNaN(parsed) || parsed <= 0) return

    const newQuantity = isWeight ? parsed / entry.serving_amount : parsed
    if (Math.abs(newQuantity - item.quantity) < 0.001) {
      cancelEdit()
      return
    }

    // Compute optimistic delta
    const qtyDelta = newQuantity - item.quantity
    if (onOptimisticUpdate) {
      onOptimisticUpdate({
        energy_kj: entry.energy_kj * qtyDelta,
        protein_g: entry.protein_g * qtyDelta,
        fat_g: entry.fat_g * qtyDelta,
        carbs_g: entry.carbs_g * qtyDelta,
      })
    }

    setSaving(true)
    setEditingId(null)
    try {
      await updateMealItem(meal.id, item.id, { quantity: newQuantity })
    } catch {
      // Revert optimistic update on error
    }
    setSaving(false)
    onRefresh()
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
        const isEditing = editingId === item.id
        const isWeight = entry && (entry.serving_unit === 'g' || entry.serving_unit === 'ml')
        return (
          <div key={item.id} className={`meal-item${isEditing ? ' meal-item-editing' : ''}`}>
            <div className="meal-item-row" onClick={() => !isEditing && startEdit(item.id)}>
              <span className="meal-item-name">
                {entry?.food_item ?? '...'}
                {item.quantity !== 1 && entry && isWeight
                  ? ` ${Math.round(entry.serving_amount * item.quantity)}${entry.serving_unit}`
                  : item.quantity !== 1 && ` x${item.quantity}`}
              </span>
              {entry && (
                <span className="meal-item-macros">
                  {displayEnergy(entry.energy_kj * item.quantity, energyUnit)} {energyLabel(energyUnit)}
                </span>
              )}
              <button className="btn-delete" onClick={(e) => { e.stopPropagation(); handleDelete(item.id) }}>&times;</button>
            </div>
            {isEditing && entry && (
              <div className="meal-item-edit">
                <label>{isWeight ? entry.serving_unit : 'qty'}</label>
                <input
                  type="number"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSave()
                    if (e.key === 'Escape') cancelEdit()
                  }}
                  autoFocus
                  min="0"
                  step="any"
                />
                <button onClick={handleSave} disabled={saving} style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}>Save</button>
                <button className="secondary" onClick={cancelEdit} style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}>Cancel</button>
              </div>
            )}
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
