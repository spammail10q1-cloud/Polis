"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, apiPost, errorMessage } from "@/lib/api";
import type { AuthResponse, Consent, User } from "@/lib/types";

type AuthContextValue = {
  user: User | null;
  consent: Consent | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    name: string;
    accept_terms: boolean;
    ai_processing: boolean;
    research_participation: boolean;
  }) => Promise<void>;
  demoLogin: () => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [consent, setConsent] = useState<Consent | null>(null);
  const [loading, setLoading] = useState(true);

  const apply = useCallback((response: AuthResponse) => {
    setUser(response.user);
    setConsent(response.consent);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const response = await apiFetch<AuthResponse>("/auth/me");
      apply(response);
    } catch {
      setUser(null);
      setConsent(null);
    }
  }, [apply]);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      setConsent(null);
    };
    window.addEventListener("polis:unauthorized", onUnauthorized);
    return () => window.removeEventListener("polis:unauthorized", onUnauthorized);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await apiFetch<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      apply(response);
    },
    [apply],
  );

  const register = useCallback<AuthContextValue["register"]>(
    async (payload) => {
      const response = await apiFetch<AuthResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      apply(response);
    },
    [apply],
  );

  const demoLogin = useCallback(async () => {
    const response = await apiPost<AuthResponse>("/auth/demo", {});
    apply(response);
  }, [apply]);

  const logout = useCallback(async () => {
    try {
      await apiPost("/auth/logout", {});
    } catch (error) {
      // A stale session should still clear locally.
      void errorMessage(error);
    }
    setUser(null);
    setConsent(null);
  }, []);

  const value = useMemo(
    () => ({ user, consent, loading, login, register, demoLogin, logout, refresh }),
    [user, consent, loading, login, register, demoLogin, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
