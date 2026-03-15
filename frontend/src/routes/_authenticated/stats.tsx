import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '../../auth.tsx'
import { getPeriodStats } from '../../api.ts'
import { prefetch, invalidate } from '../../utils/prefetch.ts'
import { displayEnergy, energyLabel } from '../../utils/energy.ts'
import type { PeriodStatsResponse, DayStats, EnergyUnit } from '../../types.ts'

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
function formatPeriodRange(startDate: string, endDate: string, period: Period): string {
  const s = new Date(`${startDate}T12:00:00Z`)
  const e = new Date(`${endDate}T12:00:00Z`)
  if (period === 'year') {
    return `${s.getUTCFullYear()}`
  }
  if (period === 'month') {
    return s.toLocaleDateString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })
  }
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

const WEEKDAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

/** Calendar grid for month view — shows Y/N/empty per day. */
function MonthCalendar({ daily, startDate }: { daily: DayStats[]; startDate: string }) {
  const lookup = new Map(daily.map((d) => [d.date, d]))
  const start = new Date(`${startDate}T12:00:00Z`)
  // Monday=0 offset: getUTCDay() is 0=Sun, so shift to Mon-based
  const firstDow = (start.getUTCDay() + 6) % 7
  const daysInMonth = daily.length

  // Build grid rows
  const cells: (DayStats | null)[] = []
  for (let i = 0; i < firstDow; i++) cells.push(null) // leading blanks
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${startDate.slice(0, 8)}${String(d).padStart(2, '0')}`
    cells.push(lookup.get(dateStr) ?? null)
  }

  const weeks: (DayStats | null)[][] = []
  for (let i = 0; i < cells.length; i += 7) {
    const row = cells.slice(i, i + 7)
    while (row.length < 7) row.push(null)
    weeks.push(row)
  }

  return (
    <div className="stats-calendar">
      <div className="stats-calendar-header">
        {WEEKDAYS.map((d, i) => (
          <span key={i} className="stats-calendar-hcell">{d}</span>
        ))}
      </div>
      {weeks.map((week, wi) => (
        <div key={wi} className="stats-calendar-row">
          {week.map((cell, ci) => {
            if (!cell) return <span key={ci} className="stats-calendar-cell" />
            const hasData = cell.consumed.energy_kj > 0 || cell.consumed.protein_g > 0
            const dayNum = new Date(`${cell.date}T12:00:00Z`).getUTCDate()
            return (
              <span
                key={ci}
                className={`stats-calendar-cell ${hasData ? (cell.on_target ? 'on-target' : 'off-target') : 'empty'}`}
                title={`${cell.date}`}
              >
                <span className="stats-calendar-day">{dayNum}</span>
                <span className="stats-calendar-status">
                  {hasData ? (cell.on_target ? 'Y' : 'N') : '\u2014'}
                </span>
              </span>
            )
          })}
        </div>
      ))}
    </div>
  )
}

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Year view — 12 months with on-target count each. */
function YearView({ daily }: { daily: DayStats[] }) {
  // Group days by month index
  const months: { total: number; onTarget: number }[] = Array.from({ length: 12 }, () => ({ total: 0, onTarget: 0 }))
  for (const day of daily) {
    const m = parseInt(day.date.slice(5, 7), 10) - 1
    const hasData = day.consumed.energy_kj > 0 || day.consumed.protein_g > 0
    months[m].total++
    if (hasData && day.on_target) months[m].onTarget++
  }

  return (
    <div className="stats-year">
      {months.map((m, i) => (
        <div key={i} className="stats-year-row">
          <span className="stats-year-month">{MONTH_NAMES[i]}</span>
          <span className="stats-year-bar">
            <span
              className="stats-year-fill"
              style={{ width: m.total > 0 ? `${(m.onTarget / m.total) * 100}%` : '0%' }}
            />
          </span>
          <span className="stats-year-count">{m.onTarget}</span>
        </div>
      ))}
    </div>
  )
}

/** Daily table for week/fortnight view. */
function DailyTable({ daily, eUnit }: { daily: DayStats[]; eUnit: EnergyUnit }) {
  return (
    <div className="stats-daily">
      {daily.map((day) => {
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
  )
}

function StatsPage() {
  const { user, signOut } = useAuth()
  const eUnit = (user?.settings?.preferred_energy_unit ?? 'kj') as EnergyUnit

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
        ? await prefetch(cacheKey, () => getPeriodStats(p, d))
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
              {formatPeriodRange(data.start_date, data.end_date, period)}
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

          {/* Period-specific breakdown */}
          {period === 'year' ? (
            <YearView daily={data.daily} />
          ) : period === 'month' ? (
            <MonthCalendar daily={data.daily} startDate={data.start_date} />
          ) : (
            <DailyTable daily={data.daily} eUnit={eUnit} />
          )}

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
