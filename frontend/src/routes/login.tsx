import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useAuth } from '../auth.tsx'
import { supabase } from '../supabase.ts'
import { useEffect } from 'react'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  const { session, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loading && session) {
      navigate({ to: '/' })
    }
  }, [loading, session, navigate])

  const signIn = (provider: 'google' | 'github') => {
    supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: window.location.origin },
    })
  }

  if (loading) return <div className="page-center">LOADING...</div>

  return (
    <div className="page-center">
      <h1 className="logo">CULINA<span className="alpha-tag">ALPHA</span></h1>
      <div className="auth-buttons">
        <button onClick={() => signIn('google')}>SIGN IN WITH GOOGLE</button>
        <button onClick={() => signIn('github')}>SIGN IN WITH GITHUB</button>
      </div>
    </div>
  )
}
