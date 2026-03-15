import type { EnergyUnit } from '../types.ts'

const KJ_PER_KCAL = 4.184

export function displayEnergy(kj: number, unit: EnergyUnit): number {
  if (unit === 'kcal') return Math.round(kj / KJ_PER_KCAL)
  return Math.round(kj)
}

export function energyLabel(unit: EnergyUnit): string {
  return unit === 'kcal' ? 'kcal' : 'kJ'
}
