import { Link, Navigate, Outlet, useLocation } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { SessionLoading } from "../../auth/components/SessionLoading";
import { useAuth } from "../../auth/hooks/useAuth";

export function RequireSettingsAdmin() {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "loading") return <SessionLoading />;
  if (status === "unauthenticated") {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (!user?.active || user.role !== "ADMIN") {
    return (
      <div className="entity-page">
        <h1>Acesso negado</h1>
        <AlertBanner>Configurações estão disponíveis somente para administradores ativos.</AlertBanner>
        <Link to="/">Voltar ao início</Link>
      </div>
    );
  }
  return <Outlet />;
}
