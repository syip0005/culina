export function todayRange(timezone: string): { start: string; end: string } {
  const now = new Date()
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const dateStr = formatter.format(now) // YYYY-MM-DD
  const start = `${dateStr}T00:00:00`
  const end = `${dateStr}T23:59:59`
  return { start, end }
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
