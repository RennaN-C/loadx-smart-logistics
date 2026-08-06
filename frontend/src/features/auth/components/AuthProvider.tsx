import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { setSessionInvalidatedHandler } from "../../../services/api";
import { clearToken, getToken, setToken } from "../../../services/tokenStorage";
import { getCurrentUser, login as loginRequest } from "../api/authApi";
import type { AuthContextValue, AuthenticatedUser, AuthStatus } from "../types";
import { AuthContext } from "./AuthContext";

interface AuthState {
  status: AuthStatus;
  user: AuthenticatedUser | null;
}

interface AuthProviderProps {
  readonly children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>(() => ({
    status: getToken() ? "loading" : "unauthenticated",
    user: null,
  }));

  useEffect(() => {
    if (!getToken()) {
      return;
    }

    let active = true;

    getCurrentUser()
      .then((user) => {
        if (active) {
          setState({ status: "authenticated", user });
        }
      })
      .catch(() => {
        clearToken();
        if (active) {
          setState({ status: "unauthenticated", user: null });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setSessionInvalidatedHandler(() => {
      clearToken();
      setState({ status: "unauthenticated", user: null });
    });

    return () => setSessionInvalidatedHandler(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginRequest(email, password);
    setToken(result.accessToken);

    const user = await getCurrentUser();
    setState({ status: "authenticated", user });
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setState({ status: "unauthenticated", user: null });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status: state.status,
      user: state.user,
      login,
      logout,
    }),
    [state.status, state.user, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
