import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import "./App.css";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [backendUser, setBackendUser] = useState<Record<string, unknown> | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signInWithGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
  };

  const signInWithGitHub = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo: window.location.origin },
    });
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setBackendUser(null);
    setBackendError(null);
  };

  const testBackend = async () => {
    if (!session) return;
    setBackendError(null);
    setBackendUser(null);

    try {
      const res = await fetch(
        `${import.meta.env.VITE_BACKEND_URL}/auth/me`,
        {
          headers: { Authorization: `Bearer ${session.access_token}` },
        }
      );
      if (!res.ok) {
        setBackendError(`${res.status} ${res.statusText}: ${await res.text()}`);
        return;
      }
      setBackendUser(await res.json());
    } catch (e) {
      setBackendError(e instanceof Error ? e.message : String(e));
    }
  };

  if (loading) return <div className="container">Loading...</div>;

  return (
    <div className="container">
      <h1>Culina Auth Test</h1>

      {!session ? (
        <div className="auth-buttons">
          <p>Sign in to test Supabase authentication</p>
          <button onClick={signInWithGoogle}>Sign in with Google</button>
          <button onClick={signInWithGitHub}>Sign in with GitHub</button>
        </div>
      ) : (
        <div className="session-info">
          <h2>Authenticated</h2>
          <dl>
            <dt>Email</dt>
            <dd>{session.user.email}</dd>
            <dt>Provider</dt>
            <dd>{session.user.app_metadata.provider}</dd>
            <dt>User ID</dt>
            <dd className="mono">{session.user.id}</dd>
            <dt>Access Token</dt>
            <dd className="mono token">{session.access_token}</dd>
          </dl>

          <div className="actions">
            <button onClick={testBackend}>Test Backend /auth/me</button>
            <button onClick={signOut} className="secondary">
              Sign Out
            </button>
          </div>

          {backendUser && (
            <div className="result success">
              <h3>Backend Response</h3>
              <pre>{JSON.stringify(backendUser, null, 2)}</pre>
            </div>
          )}

          {backendError && (
            <div className="result error">
              <h3>Backend Error</h3>
              <pre>{backendError}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
