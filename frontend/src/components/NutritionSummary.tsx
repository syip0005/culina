interface Props {
  energyKj: number
  proteinG: number
  fatG: number
  carbsG: number
  quantity?: number
}

export function NutritionSummary({ energyKj, proteinG, fatG, carbsG, quantity = 1 }: Props) {
  const e = Math.round(energyKj * quantity)
  const p = Math.round(proteinG * quantity * 10) / 10
  const f = Math.round(fatG * quantity * 10) / 10
  const c = Math.round(carbsG * quantity * 10) / 10

  return (
    <div className="nutrition-row">
      <span>{e} kJ</span>
      <span>{p}p</span>
      <span>{f}f</span>
      <span>{c}c</span>
    </div>
  )
}
