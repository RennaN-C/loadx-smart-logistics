import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { AlertBanner } from "../components/AlertBanner";
import { useAuth } from "../features/auth/hooks/useAuth";
import { canManageLogistics } from "../features/auth/permissions";

/** Projeção das permissões de leitura; o backend continua autorizando cada recurso. */
export function OperationalAccess({ children, overview = false }: { readonly children: ReactNode; readonly overview?: boolean }) {
  const { user } = useAuth();
  const allowed = user?.active && (canManageLogistics(user.role) || (!overview && user.role === "CHECKER"));
  if (!allowed) return <div className="entity-page"><h1>Acesso negado</h1><AlertBanner>Seu perfil não tem permissão para consultar esta área.</AlertBanner><Link to="/">Voltar à visão geral</Link></div>;
  return children;
}
