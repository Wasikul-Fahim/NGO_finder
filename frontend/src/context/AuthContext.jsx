import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import * as authApi from "../api/auth";
import { setAccessToken, setAuthLostHandler } from "../api/client";

const AuthContext = createContext(null);

export const ROLE_HOME = {
  NGO_ADMIN: "/admin",
  PLATFORM_ADMIN: "/platform",
  VOLUNTEER: "/dashboard",
  DONOR: "/campaigns",
  BENEFICIARY: "/support",
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const applySession = useCallback((data) => {
    setAccessToken(data?.access_token ?? null);
    setUser(data?.user ?? null);
  }, []);

  // App start: the refresh cookie (if any) gives us a fresh access token and the user.
  useEffect(() => {
    let active = true;
    authApi.restoreSession()
      .then((data) => active && applySession(data))
      .catch(() => active && applySession(null))
      .finally(() => active && setIsLoading(false));
    setAuthLostHandler(() => applySession(null));
    return () => { active = false; };
  }, [applySession]);

  const login = useCallback(async (credentials) => {
    const data = await authApi.login(credentials);
    applySession(data);
    return data.user;
  }, [applySession]);

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch { /* cookie is cleared server-side when reachable; clear local state regardless */ }
    applySession(null);
  }, [applySession]);

  const value = useMemo(
    () => ({ user, isLoading, isAuthenticated: !!user, login, logout, register: authApi.register, registerNgo: authApi.registerNgo }),
    [user, isLoading, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
