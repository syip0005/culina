import { createFileRoute, Link } from '@tanstack/react-router'
import { useAuth } from '../../auth.tsx'
import { getSettings, updateSettings } from '../../api.ts'
import { consume, invalidate } from '../../utils/prefetch.ts'
import { useEffect, useState } from 'react'
import type { UserSettings, GoalMode } from '../../types.ts'

export const Route = createFileRoute('/_authenticated/settings')({
  component: SettingsPage,
})

function SettingsPage() {
  const { user, signOut } = useAuth()
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [energyTarget, setEnergyTarget] = useState('')
  const [proteinTarget, setProteinTarget] = useState('')
  const [fatTarget, setFatTarget] = useState('')
  const [carbsTarget, setCarbsTarget] = useState('')
  const [timezone, setTimezone] = useState('')
  const [energyUnit, setEnergyUnit] = useState('kj')
  const [goalModes, setGoalModes] = useState<Record<string, GoalMode>>({
    energy_kj: 'under',
    protein_g: 'over',
    fat_g: 'under',
    carbs_g: 'under',
  })
  const [withinPct, setWithinPct] = useState('10')

  useEffect(() => {
    consume('settings', () => getSettings()).then((s) => {
      setSettings(s)
      setEnergyTarget(s.daily_energy_target_kj?.toString() ?? '')
      setProteinTarget(s.daily_protein_target_g?.toString() ?? '')
      setFatTarget(s.daily_fat_target_g?.toString() ?? '')
      setCarbsTarget(s.daily_carbs_target_g?.toString() ?? '')
      setTimezone(s.timezone)
      setEnergyUnit(s.preferred_energy_unit)
      if (s.extra?.goal_modes) {
        setGoalModes(s.extra.goal_modes as Record<string, GoalMode>)
      }
      if (s.extra?.goal_within_pct != null) {
        setWithinPct(String(s.extra.goal_within_pct))
      }
    })
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      invalidate('settings')
      const updated = await updateSettings({
        daily_energy_target_kj: energyTarget ? parseFloat(energyTarget) : null,
        daily_protein_target_g: proteinTarget ? parseFloat(proteinTarget) : null,
        daily_fat_target_g: fatTarget ? parseFloat(fatTarget) : null,
        daily_carbs_target_g: carbsTarget ? parseFloat(carbsTarget) : null,
        timezone,
        preferred_energy_unit: energyUnit,
        extra: {
          ...settings?.extra,
          goal_modes: goalModes,
          goal_within_pct: withinPct ? parseFloat(withinPct) : 10,
        },
      })
      setSettings(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (!settings) return <div className="container">LOADING...</div>

  return (
    <div className="container">
      <div className="header">
        <h1>Settings</h1>
        <div className="header-actions">
          <Link to="/">&larr; Back</Link>
          <span className="header-sep">/</span>
          <button className="link-button" onClick={signOut}>Logout</button>
        </div>
      </div>

      <div className="form-group">
        <label>Email</label>
        <input type="text" value={user?.email ?? ''} disabled />
      </div>

      <div className="form-group">
        <label>Display Name</label>
        <input type="text" value={user?.display_name ?? ''} disabled />
      </div>

      <h2 style={{ marginBottom: '0.75rem', marginTop: '1rem' }}>Daily Targets</h2>

      <div className="form-row">
        <div className="form-group">
          <label>Energy (kJ)</label>
          <input
            type="number"
            value={energyTarget}
            onChange={(e) => setEnergyTarget(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Protein (g)</label>
          <input
            type="number"
            value={proteinTarget}
            onChange={(e) => setProteinTarget(e.target.value)}
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Fat (g)</label>
          <input
            type="number"
            value={fatTarget}
            onChange={(e) => setFatTarget(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Carbs (g)</label>
          <input
            type="number"
            value={carbsTarget}
            onChange={(e) => setCarbsTarget(e.target.value)}
          />
        </div>
      </div>

      <div className="form-group">
        <label>Timezone</label>
        <input
          type="text"
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
        />
      </div>

      <div className="form-group">
        <label>Preferred Energy Unit</label>
        <select value={energyUnit} onChange={(e) => setEnergyUnit(e.target.value)}>
          <option value="kj">kJ</option>
          <option value="kcal">kcal</option>
        </select>
      </div>

      <h2 style={{ marginBottom: '0.75rem', marginTop: '1rem' }}>Goal Modes</h2>
      <p className="text-muted text-xs" style={{ marginBottom: '0.75rem' }}>
        How each macro is evaluated when checking if you hit your daily target.
      </p>

      {([
        ['energy_kj', 'Energy'],
        ['protein_g', 'Protein'],
        ['fat_g', 'Fat'],
        ['carbs_g', 'Carbs'],
      ] as const).map(([field, label]) => (
        <div key={field} className="form-group">
          <label>{label}</label>
          <select
            value={goalModes[field] ?? 'under'}
            onChange={(e) => setGoalModes((prev) => ({ ...prev, [field]: e.target.value as GoalMode }))}
          >
            <option value="under">Stay under target</option>
            <option value="over">Meet or exceed target</option>
            <option value="within">Within tolerance</option>
          </select>
        </div>
      ))}

      {Object.values(goalModes).includes('within') && (
        <div className="form-group">
          <label>Tolerance %</label>
          <input
            type="number"
            value={withinPct}
            onChange={(e) => setWithinPct(e.target.value)}
            min="1"
            max="50"
          />
        </div>
      )}

      {error && <p style={{ color: 'red', marginBottom: '0.75rem' }}>{error}</p>}

      <button onClick={handleSave} disabled={saving} style={{ width: '100%', marginBottom: '0.75rem' }}>
        {saving ? 'SAVING...' : 'SAVE SETTINGS'}
      </button>

      <button className="secondary" onClick={signOut} style={{ width: '100%' }}>
        SIGN OUT
      </button>
    </div>
  )
}
