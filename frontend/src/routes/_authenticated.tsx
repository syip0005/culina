import { createFileRoute, Outlet, useNavigate } from '@tanstack/react-router'
import { useAuth } from '../auth.tsx'
import { useEffect } from 'react'
import { getPeriodStats, getSettings } from '../api.ts'
import { prefetch } from '../utils/prefetch.ts'

export const Route = createFileRoute('/_authenticated')({
  component: AuthenticatedLayout,
})

function AuthenticatedLayout() {
  const { session, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loading && !session) {
      navigate({ to: '/login' })
    }
  }, [loading, session, navigate])

  // Prefetch stats and settings data once authenticated
  useEffect(() => {
    if (session) {
      prefetch('stats:week', () => getPeriodStats('week'))
      prefetch('settings', () => getSettings())
    }
  }, [session])

  if (loading) return <div className="page-center">LOADING...</div>
  if (!session) return null

  return <Outlet />
}
