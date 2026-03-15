import { useState } from 'react'
import { updateNutritionEntry } from '../api.ts'
import type { NutritionEntry, ServingUnit } from '../types.ts'

interface Props {
  entry: NutritionEntry
  energyUnit?: string
  onSave: (updated: NutritionEntry) => void
  onClose: () => void
}

export function EditEntryPanel({ entry, onSave, onClose }: Props) {
  const [foodItem, setFoodItem] = useState(entry.food_item)
  const [brand, setBrand] = useState(entry.brand)
  const [servingAmount, setServingAmount] = useState(String(entry.serving_amount))
  const [servingUnit, setServingUnit] = useState<ServingUnit>(entry.serving_unit)
  const [servingDescription, setServingDescription] = useState(entry.serving_description ?? '')
  const [energyKj, setEnergyKj] = useState(String(entry.energy_kj))
  const [proteinG, setProteinG] = useState(String(entry.protein_g))
  const [fatG, setFatG] = useState(String(entry.fat_g))
  const [carbsG, setCarbsG] = useState(String(entry.carbs_g))
  const [notes, setNotes] = useState(entry.notes ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    const changes: Record<string, unknown> = {}

    if (foodItem.trim() !== entry.food_item) changes.food_item = foodItem.trim()
    if (brand !== entry.brand) changes.brand = brand
    const sa = parseFloat(servingAmount)
    if (!isNaN(sa) && sa !== entry.serving_amount) changes.serving_amount = sa
    if (servingUnit !== entry.serving_unit) changes.serving_unit = servingUnit
    const sd = servingDescription || null
    if (sd !== entry.serving_description) changes.serving_description = sd
    const ek = parseFloat(energyKj)
    if (!isNaN(ek) && ek !== entry.energy_kj) changes.energy_kj = ek
    const pg = parseFloat(proteinG)
    if (!isNaN(pg) && pg !== entry.protein_g) changes.protein_g = pg
    const fg = parseFloat(fatG)
    if (!isNaN(fg) && fg !== entry.fat_g) changes.fat_g = fg
    const cg = parseFloat(carbsG)
    if (!isNaN(cg) && cg !== entry.carbs_g) changes.carbs_g = cg
    const n = notes || null
    if (n !== entry.notes) changes.notes = n

    if (Object.keys(changes).length === 0) {
      onClose()
      return
    }

    if (!foodItem.trim()) {
      setError('Name is required')
      return
    }

    setSaving(true)
    setError(null)
    try {
      const updated = await updateNutritionEntry(entry.id, changes)
      onSave(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="overlay second">
      <div className="overlay-inner">
        <div className="overlay-header">
          <h2>Edit Entry</h2>
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
