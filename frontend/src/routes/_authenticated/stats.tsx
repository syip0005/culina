import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '../../auth.tsx'
import { getPeriodStats } from '../../api.ts'
import { consume, invalidate } from '../../utils/prefetch.ts'
import { displayEnergy, energyLabel } from '../../utils/energy.ts'
import type { PeriodStatsResponse } from '../../types.ts'

export const Route = createFileRoute('/_authenticated/stats')({
  component: StatsPage,
})

type Period = 'week' | 'fortnight' | 'month' | 'year'

const PERIODS: Period[] = ['week', 'fortnight', 'month', 'year']

/** Format a YYYY-MM-DD into "Mon 9" style short label. */
function shortDay(dateStr: string): string {
  const d = new Date(`${dateStr}T12:00:00Z`)
  const day = d.toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' })
  return `${day} ${d.getUTCDate()}`
}

/** Format period range like "Mar 9 - Mar 15, 2026". */
function formatPeriodRange(startDate: string, endDate: string): string {
  const s = new Date(`${startDate}T12:00:00Z`)
  const e = new Date(`${endDate}T12:00:00Z`)
  const sMonth = s.toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' })
  const eMonth = e.toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' })
  const eYear = e.getUTCFullYear()
  if (sMonth === eMonth) {
    return `${sMonth} ${s.getUTCDate()} - ${e.getUTCDate()}, ${eYear}`
  }
  return `${sMonth} ${s.getUTCDate()} - ${eMonth} ${e.getUTCDate()}, ${eYear}`
}

/** Shift a period by +1 or -1 step. Returns a date string in the shifted period. */
function shiftPeriod(startDate: string, endDate: string, period: Period, direction: -1 | 1): string {
  const s = new Date(`${startDate}T12:00:00Z`)
  const e = new Date(`${endDate}T12:00:00Z`)
  if (period === 'week') {
    s.setUTCDate(s.getUTCDate() + direction * 7)
  } else if (period === 'fortnight') {
    s.setUTCDate(s.getUTCDate() + direction * 14)
  } else if (period === 'month') {
    s.setUTCMonth(s.getUTCMonth() + direction)
  } else if (period === 'year') {
    s.setUTCFullYear(s.getUTCFullYear() + direction)
  }
  // For backwards, the start of previous period; for forwards, one day past end
  if (direction === 1) {
    e.setUTCDate(e.getUTCDate() + 1)
    return e.toISOString().slice(0, 10)
  }
  return s.toISOString().slice(0, 10)
}

function StatsPage() {
  const { user, signOut } = useAuth()
  const eUnit = user?.settings?.preferred_energy_unit ?? 'kj'

  const [period, setPeriod] = useState<Period>('week')
  const [refDate, setRefDate] = useState<string | undefined>(undefined)
  const [data, setData] = useState<PeriodStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async (p: Period, d?: string) => {
    setLoading(true)
    setError(null)
    try {
      // Use prefetch cache for default view (week, current period)
      const cacheKey = d ? undefined : `stats:${p}`
      const result = cacheKey
        ? await consume(cacheKey, () => getPeriodStats(p, d))
        : await getPeriodStats(p, d)
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load stats')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats(period, refDate)
  }, [period, refDate, fetchStats])

  const navigatePeriod = useCallback((direction: -1 | 1) => {
    if (!data) return
    const next = shiftPeriod(data.start_date, data.end_date, period, direction)
    setRefDate(next)
  }, [data, period])

  const handlePeriodChange = useCallback((p: Period) => {
    invalidate(`stats:${period}`)
    setPeriod(p)
    setRefDate(undefined) // reset to current period
  }, [period])

  return (
    <div className="container">
      <div className="header">
        <h1>Stats</h1>
        <div className="header-actions">
          <Link to="/">Home</Link>
          <span className="header-sep">/</span>
          <Link to="/settings">Settings</Link>
          <span className="header-sep">/</span>
          <button className="link-button" onClick={signOut}>Logout</button>
        </div>
      </div>

      {/* Period selector */}
      <div className="stats-period-selector">
        {PERIODS.map((p) => (
          <button
            key={p}
            className={p === period ? '' : 'secondary'}
            onClick={() => handlePeriodChange(p)}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Period navigation */}
      {data && (
        <div className="day-nav">
          <button className="day-nav-btn" onClick={() => navigatePeriod(-1)} aria-label="Previous period">&larr;</button>
          <div className="day-nav-label">
            <span className="day-nav-text">
              {formatPeriodRange(data.start_date, data.end_date)}
            </span>
          </div>
          <button className="day-nav-btn" onClick={() => navigatePeriod(1)} aria-label="Next period">&rarr;</button>
        </div>
      )}

      {loading && <div style={{ textAlign: 'center', padding: '2rem 0' }}>LOADING...</div>}
      {error && <div style={{ textAlign: 'center', padding: '2rem 0', color: 'red' }}>{error}</div>}

      {data && !loading && (
        <>
          {/* Days on target headline */}
          <div className="stats-headline">
            <span className="stats-headline-number">{data.days_on_target}</span>
            <span className="stats-headline-sep">/</span>
            <span className="stats-headline-total">{data.days_in_period}</span>
            <span className="stats-headline-label">days on target</span>
          </div>

          {/* Daily breakdown */}
          <div className="stats-daily">
            {data.daily.map((day) => {
              const hasData = day.consumed.energy_kj > 0 || day.consumed.protein_g > 0
              return (
                <div key={day.date} className={`stats-day-row ${!hasData ? 'stats-day-empty' : ''}`}>
                  <span className="stats-day-label">{shortDay(day.date)}</span>
                  {hasData ? (
                    <>
                      <span className="stats-day-macros">
                        {displayEnergy(day.consumed.energy_kj, eUnit)}{energyLabel(eUnit)}
                        {' '}{Math.round(day.consumed.protein_g)}p
                        {' '}{Math.round(day.consumed.fat_g)}f
                        {' '}{Math.round(day.consumed.carbs_g)}c
                      </span>
                      <span className={`stats-day-status ${day.on_target ? 'on-target' : 'off-target'}`}>
                        {day.on_target ? 'Y' : 'N'}
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="stats-day-macros text-muted">&mdash;</span>
                      <span className="stats-day-status text-muted">&mdash;</span>
                    </>
                  )}
                </div>
              )
            })}
          </div>

          {/* Averages */}
          {data.days_logged > 0 && (
            <div className="stats-averages">
              <div className="stats-averages-label">
                Averages ({data.days_logged} logged {data.days_logged === 1 ? 'day' : 'days'})
              </div>
              <div className="stats-averages-values">
                {displayEnergy(data.average_consumed.energy_kj, eUnit)} {energyLabel(eUnit)}
                {' | '}{Math.round(data.average_consumed.protein_g)}p
                {' | '}{Math.round(data.average_consumed.fat_g)}f
                {' | '}{Math.round(data.average_consumed.carbs_g)}c
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
