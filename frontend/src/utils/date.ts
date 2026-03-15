/**
 * Get the UTC offset (in ms) for a named timezone at a given instant.
 * Positive means the timezone is ahead of UTC (e.g. +11h for AEST).
 */
function tzOffsetMs(timezone: string, at: Date): number {
  const utcStr = at.toLocaleString('en-US', { timeZone: 'UTC' })
  const tzStr = at.toLocaleString('en-US', { timeZone: timezone })
  return new Date(tzStr).getTime() - new Date(utcStr).getTime()
}

/** UTC start/end for a given YYYY-MM-DD in the user's timezone. */
export function dateRange(dateStr: string, timezone: string): { start: string; end: string } {
  const midnightAsUTC = new Date(`${dateStr}T00:00:00Z`)
  const offset = tzOffsetMs(timezone, midnightAsUTC)
  const startUTC = new Date(midnightAsUTC.getTime() - offset)
  const endUTC = new Date(startUTC.getTime() + 24 * 60 * 60 * 1000 - 1000)
  return { start: startUTC.toISOString(), end: endUTC.toISOString() }
}

export function todayRange(timezone: string): { start: string; end: string } {
  return dateRange(todayDateStr(timezone), timezone)
}

export function todayDateStr(timezone: string): string {
  const now = new Date()
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  return formatter.format(now)
}

/** Shift a YYYY-MM-DD string by N days (negative = past). */
export function shiftDate(dateStr: string, days: number): string {
  const d = new Date(`${dateStr}T12:00:00Z`) // noon to avoid DST edge cases
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

/** Return a UTC ISO timestamp representing noon on a YYYY-MM-DD in the given timezone. */
export function dateMidpointISO(dateStr: string, timezone: string): string {
  const noonAsUTC = new Date(`${dateStr}T12:00:00Z`)
  const offset = tzOffsetMs(timezone, noonAsUTC)
  return new Date(noonAsUTC.getTime() - offset).toISOString()
}

/** Format YYYY-MM-DD for display: "Today", "Yesterday", or "Mon 14 Mar" */
export function formatDateLabel(dateStr: string, todayStr: string): string {
  if (dateStr === todayStr) return 'Today'
  if (dateStr === shiftDate(todayStr, -1)) return 'Yesterday'
  if (dateStr === shiftDate(todayStr, 1)) return 'Tomorrow'
  const d = new Date(`${dateStr}T12:00:00Z`)
  const day = d.toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' })
  const date = d.getUTCDate()
  const month = d.toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' })
  return `${day} ${date} ${month}`
}
