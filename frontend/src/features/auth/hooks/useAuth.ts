import { useContext } from "react";

import { AuthContext } from "../components/AuthContext";
import type { AuthContextValue } from "../types";

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth deve ser usado dentro de um AuthProvider.");
  }

  return context;
}
