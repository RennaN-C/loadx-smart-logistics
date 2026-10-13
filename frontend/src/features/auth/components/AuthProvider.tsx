import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { setSessionInvalidatedHandler } from "../../../services/api";
import { clearCsrfToken } from "../../../services/csrfToken";
import { getCurrentUser, login as loginRequest, logout as logoutRequest } from "../api/authApi";
import type { AuthContextValue, AuthenticatedUser, AuthStatus } from "../types";
import type { MfaChallenge } from "../mfaTypes";
import { AuthContext } from "./AuthContext";

interface AuthState {
  status: AuthStatus;
  user: AuthenticatedUser | null;
  pendingMfa?: MfaChallenge;
  accountNotice?: "password-changed" | "session-revoked";
}

interface AuthProviderProps {
  readonly children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>(() => ({
    status: "loading",
    user: null,
  }));

  useEffect(() => {
    let active = true;

    getCurrentUser()
      .then((user) => {
        if (active) {
          setState({ status: "authenticated", user });
        }
      })
      .catch(() => {
        clearCsrfToken();
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
      clearCsrfToken();
      setState({ status: "unauthenticated", user: null });
    });

    return () => setSessionInvalidatedHandler(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const user = await loginRequest(email, password);
    setState({ status: "authenticated", user });
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    clearCsrfToken();
    setState({ status: "unauthenticated", user: null });
  }, []);

  const updateUser = useCallback((user: AuthenticatedUser | null, accountNotice?: "password-changed" | "session-revoked") => {
    if (user === null) clearCsrfToken();
    setState({ status: user ? "authenticated" : "unauthenticated", user, accountNotice });
  }, []);

  const beginMfa = useCallback((pendingMfa: MfaChallenge | undefined) => {
    clearCsrfToken();
    setState({ status: "unauthenticated", user: null, pendingMfa });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status: state.status,
      user: state.user,
      login,
      logout,
      updateUser,
      accountNotice: state.accountNotice,
      pendingMfa: state.pendingMfa,
      beginMfa,
    }),
    [state.status, state.user, state.accountNotice, state.pendingMfa, beginMfa, login, logout, updateUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
