/**
 * Get the UTC offset (in ms) for a named timezone at a given instant.
 * Positive means the timezone is ahead of UTC (e.g. +11h for AEST).
 */
function tzOffsetMs(timezone: string, at: Date): number {
  const utcStr = at.toLocaleString('en-US', { timeZone: 'UTC' })
  const tzStr = at.toLocaleString('en-US', { timeZone: timezone })
  return new Date(tzStr).getTime() - new Date(utcStr).getTime()
}

export function todayRange(timezone: string): { start: string; end: string } {
  const now = new Date()
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const dateStr = formatter.format(now) // YYYY-MM-DD in user's timezone

  // Local midnight as if it were UTC, then subtract the TZ offset to get true UTC
  const midnightAsUTC = new Date(`${dateStr}T00:00:00Z`)
  const offset = tzOffsetMs(timezone, midnightAsUTC)
  const startUTC = new Date(midnightAsUTC.getTime() - offset)
  const endUTC = new Date(startUTC.getTime() + 24 * 60 * 60 * 1000 - 1000)

  return { start: startUTC.toISOString(), end: endUTC.toISOString() }
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
