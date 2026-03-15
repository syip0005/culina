/** Simple promise cache for prefetching data across routes. */

const cache = new Map<string, { promise: Promise<unknown>; ts: number }>()

/** Max age before a cached entry is considered stale (ms). */
const MAX_AGE = 60_000

/**
 * Prefetch a value by key. If already cached and fresh, does nothing.
 * Returns the promise (callers can ignore it for fire-and-forget).
 */
export function prefetch<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = cache.get(key)
  if (existing && Date.now() - existing.ts < MAX_AGE) {
    return existing.promise as Promise<T>
  }
  const promise = fn()
  cache.set(key, { promise, ts: Date.now() })
  // Clean up on rejection so it retries next time
  promise.catch(() => cache.delete(key))
  return promise
}

/**
 * Consume a prefetched value. Returns the cached promise if available,
 * otherwise calls fn() and caches the result.
 */
export function consume<T>(key: string, fn: () => Promise<T>): Promise<T> {
  return prefetch(key, fn)
}

/** Invalidate a specific cache key (e.g. after a mutation). */
export function invalidate(key: string) {
  cache.delete(key)
}

/** Invalidate all cache keys matching a prefix (e.g. "stats:" clears all period stats). */
export function invalidatePrefix(prefix: string) {
  for (const key of cache.keys()) {
    if (key.startsWith(prefix)) cache.delete(key)
  }
}

/** Invalidate and immediately re-prefetch (fire-and-forget). */
export function refetch<T>(key: string, fn: () => Promise<T>): void {
  cache.delete(key)
  prefetch(key, fn)
}
