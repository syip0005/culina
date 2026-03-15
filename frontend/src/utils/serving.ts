import type { ServingUnit } from '../types.ts'

/** Units where the user adjusts a weight/volume amount (g, ml) vs count-based (piece, serve). */
export function isScalableUnit(unit: ServingUnit): boolean {
  return unit === 'g' || unit === 'ml'
}

export function servingLabel(amount: number, unit: ServingUnit, description: string | null): string {
  if (isScalableUnit(unit)) {
    return `${amount}${unit}${description ? ` (${description})` : ''}`
  }
  if (description) return description
  return `${amount} ${unit}${amount !== 1 ? 's' : ''}`
}
