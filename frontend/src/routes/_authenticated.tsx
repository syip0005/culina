import { createFileRoute, Outlet, useNavigate } from '@tanstack/react-router'
import { useAuth } from '../auth.tsx'
import { useEffect } from 'react'

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

  if (loading) return <div className="page-center">LOADING...</div>
  if (!session) return null

  return <Outlet />
}
