import { displayEnergy, energyLabel } from '../utils/energy.ts'
import type { EnergyUnit } from '../types.ts'

interface Props {
  energyKj: number
  proteinG: number
  fatG: number
  carbsG: number
  quantity?: number
  energyUnit?: EnergyUnit
}

export function NutritionSummary({ energyKj, proteinG, fatG, carbsG, quantity = 1, energyUnit = 'kj' }: Props) {
  const e = displayEnergy(energyKj * quantity, energyUnit)
  const p = Math.round(proteinG * quantity * 10) / 10
  const f = Math.round(fatG * quantity * 10) / 10
  const c = Math.round(carbsG * quantity * 10) / 10

  return (
    <div className="nutrition-row">
      <span>{e} {energyLabel(energyUnit)}</span>
      <span>{p}p</span>
      <span>{f}f</span>
      <span>{c}c</span>
    </div>
  )
}
