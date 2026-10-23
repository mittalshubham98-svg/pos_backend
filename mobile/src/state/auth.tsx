import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { api, ApiError, DEFAULT_API_URL, normaliseBaseUrl } from '@/lib/api';
import { storage } from '@/lib/storage';

type Session = { token: string; custCode: string; name: string | null; expiresAt: number };

type AuthState = {
  status: 'loading' | 'signedOut' | 'signedIn';
  session: Session | null;
  apiUrl: string;
  signIn: (apiUrl: string, custCode: string, password: string) => Promise<void>;
  signOut: () => void;
  /** Wrap authed API calls: a 401 means the token expired or was revoked -> back to login. */
  handleAuthError: (err: unknown) => void;
};

const SESSION_KEY = 'auth_session';
const API_URL_KEY = 'api_url';

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState['status']>('loading');
  const [session, setSession] = useState<Session | null>(null);
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);

  useEffect(() => {
    (async () => {
      try {
        const [rawSession, savedUrl] = await Promise.all([
          storage.get(SESSION_KEY),
          storage.get(API_URL_KEY),
        ]);
        if (savedUrl) setApiUrl(savedUrl);
        const saved: Session | null = rawSession ? JSON.parse(rawSession) : null;
        if (saved && saved.expiresAt > Date.now()) {
          setSession(saved);
          setStatus('signedIn');
          return;
        }
      } catch {
        // Unreadable storage just means signing in again.
      }
      setStatus('signedOut');
    })();
  }, []);

  const signIn = useCallback(async (rawUrl: string, custCode: string, password: string) => {
    const url = normaliseBaseUrl(rawUrl) || DEFAULT_API_URL;
    const res = await api.login(url, custCode.trim().toUpperCase(), password);
    const next: Session = {
      token: res.token,
      custCode: res.cust_code,
      name: res.name,
      // Renew a minute early so a request never goes out with a token about to lapse.
      expiresAt: Date.now() + (res.expires_in_minutes - 1) * 60_000,
    };
    await Promise.all([
      storage.set(SESSION_KEY, JSON.stringify(next)),
      storage.set(API_URL_KEY, url),
    ]);
    setApiUrl(url);
    setSession(next);
    setStatus('signedIn');
  }, []);

  const signOut = useCallback(() => {
    storage.remove(SESSION_KEY).catch(() => {});
    setSession(null);
    setStatus('signedOut');
  }, []);

  const handleAuthError = useCallback(
    (err: unknown) => {
      if (err instanceof ApiError && err.status === 401) signOut();
    },
    [signOut],
  );

  const value = useMemo(
    () => ({ status, session, apiUrl, signIn, signOut, handleAuthError }),
    [status, session, apiUrl, signIn, signOut, handleAuthError],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
