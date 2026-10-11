import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { BrandPanel } from "../components/BrandPanel";
import { LoginForm } from "../components/LoginForm";
import { SessionLoading } from "../components/SessionLoading";
import "./LoginPage.css";

interface LocationState {
  from?: { pathname: string };
  accountNotice?: "password-changed" | "session-revoked";
}

export function LoginPage() {
  const { status, accountNotice } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <SessionLoading />;
  }

  if (status === "authenticated") {
    const state = location.state as LocationState | null;
    const redirectTo = state?.from?.pathname ?? "/";
    return <Navigate to={redirectTo} replace />;
  }

  return (
    <div className="login-page">
      <BrandPanel />
      <main className="login-formside">
        {accountNotice === "password-changed" && <output>Senha alterada. Todas as sessões foram encerradas; entre novamente.</output>}
        {accountNotice === "session-revoked" && <output>Sessão encerrada. Entre novamente para continuar.</output>}
        <LoginForm />
      </main>
    </div>
  );
}
