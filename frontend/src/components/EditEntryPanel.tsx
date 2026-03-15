import { useState } from 'react'
import { updateNutritionEntry } from '../api.ts'
import type { NutritionEntry, SearchNutritionInfo, ServingUnit, EnergyUnit } from '../types.ts'

interface EditableFields {
  food_item: string
  brand: string
  serving_amount: number
  serving_unit: ServingUnit
  serving_description: string | null
  energy_kj: number
  protein_g: number
  fat_g: number
  carbs_g: number
  notes: string | null
}

type Props = {
  className?: string
  energyUnit?: EnergyUnit
  title?: string
  onClose: () => void
} & (
  | { entry: NutritionEntry; item?: never; onSave: (updated: NutritionEntry) => void }
  | { item: SearchNutritionInfo; entry?: never; onSave: (updated: SearchNutritionInfo) => void }
)

export function EditEntryPanel({ entry, item, className, title, onSave, onClose }: Props) {
  const source: EditableFields = entry ?? item!
  const [foodItem, setFoodItem] = useState(source.food_item)
  const [brand, setBrand] = useState(source.brand)
  const [servingAmount, setServingAmount] = useState(String(source.serving_amount))
  const [servingUnit, setServingUnit] = useState<ServingUnit>(source.serving_unit)
  const [servingDescription, setServingDescription] = useState(source.serving_description ?? '')
  const [energyKj, setEnergyKj] = useState(String(source.energy_kj))
  const [proteinG, setProteinG] = useState(String(source.protein_g))
  const [fatG, setFatG] = useState(String(source.fat_g))
  const [carbsG, setCarbsG] = useState(String(source.carbs_g))
  const [notes, setNotes] = useState(source.notes ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    if (!foodItem.trim()) {
      setError('Name is required')
      return
    }

    if (item) {
      // Local mode: build updated SearchNutritionInfo, no API call
      const updated: SearchNutritionInfo = {
        ...item,
        food_item: foodItem.trim(),
        brand,
        serving_amount: parseFloat(servingAmount) || item.serving_amount,
        serving_unit: servingUnit,
        serving_description: servingDescription || null,
        energy_kj: parseFloat(energyKj) || 0,
        protein_g: parseFloat(proteinG) || 0,
        fat_g: parseFloat(fatG) || 0,
        carbs_g: parseFloat(carbsG) || 0,
        notes: notes || null,
      };
      (onSave as (updated: SearchNutritionInfo) => void)(updated)
      return
    }

    // Persisted mode: build diff, PATCH via API
    const changes: Record<string, unknown> = {}

    if (foodItem.trim() !== source.food_item) changes.food_item = foodItem.trim()
    if (brand !== source.brand) changes.brand = brand
    const sa = parseFloat(servingAmount)
    if (!isNaN(sa) && sa !== source.serving_amount) changes.serving_amount = sa
    if (servingUnit !== source.serving_unit) changes.serving_unit = servingUnit
    const sd = servingDescription || null
    if (sd !== source.serving_description) changes.serving_description = sd
    const ek = parseFloat(energyKj)
    if (!isNaN(ek) && ek !== source.energy_kj) changes.energy_kj = ek
    const pg = parseFloat(proteinG)
    if (!isNaN(pg) && pg !== source.protein_g) changes.protein_g = pg
    const fg = parseFloat(fatG)
    if (!isNaN(fg) && fg !== source.fat_g) changes.fat_g = fg
    const cg = parseFloat(carbsG)
    if (!isNaN(cg) && cg !== source.carbs_g) changes.carbs_g = cg
    const n = notes || null
    if (n !== source.notes) changes.notes = n

    if (Object.keys(changes).length === 0) {
      onClose()
      return
    }

    setSaving(true)
    setError(null)
    try {
      const updated = await updateNutritionEntry(entry!.id, changes)
      onSave(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={className ?? "overlay second"}>
      <div className="overlay-inner">
        <div className="overlay-header">
          <h2>{title ?? 'Edit Entry'}</h2>
          <button className="secondary" onClick={onClose} style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
            Cancel
          </button>
        </div>

        <div className="overlay-body">
          <div className="form-group">
            <label>Name</label>
            <input type="text" value={foodItem} onChange={(e) => setFoodItem(e.target.value)} required />
          </div>

          <div className="form-group">
            <label>Brand</label>
            <input type="text" value={brand} onChange={(e) => setBrand(e.target.value)} />
          </div>

          <div className="form-group">
            <label>Serving</label>
            <div className="edit-serving-row">
              <div className="form-group">
                <input type="number" value={servingAmount} onChange={(e) => setServingAmount(e.target.value)} step="any" min="0" />
              </div>
              <div className="form-group">
                <select value={servingUnit} onChange={(e) => setServingUnit(e.target.value as ServingUnit)}>
                  <option value="g">g</option>
                  <option value="ml">ml</option>
                  <option value="piece">piece</option>
                  <option value="serve">serve</option>
                </select>
              </div>
              <div className="form-group">
                <input type="text" value={servingDescription} onChange={(e) => setServingDescription(e.target.value)} placeholder="e.g. 1 medium apple" />
              </div>
            </div>
          </div>

          <div className="form-row" style={{ marginBottom: '0.75rem' }}>
            <div className="form-group">
              <label>Energy (kJ)</label>
              <input type="number" value={energyKj} onChange={(e) => setEnergyKj(e.target.value)} step="any" min="0" />
            </div>
            <div className="form-group">
              <label>Protein (g)</label>
              <input type="number" value={proteinG} onChange={(e) => setProteinG(e.target.value)} step="any" min="0" />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Fat (g)</label>
              <input type="number" value={fatG} onChange={(e) => setFatG(e.target.value)} step="any" min="0" />
            </div>
            <div className="form-group">
              <label>Carbs (g)</label>
              <input type="number" value={carbsG} onChange={(e) => setCarbsG(e.target.value)} step="any" min="0" />
            </div>
          </div>

          <div className="form-group" style={{ marginTop: '0.75rem' }}>
            <label>Notes</label>
            <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <div className="overlay-footer">
          {error && <div className="delete-error text-xs" style={{ marginBottom: '0.5rem' }}>{error}</div>}
          <button onClick={handleSave} disabled={saving} style={{ width: '100%' }}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
