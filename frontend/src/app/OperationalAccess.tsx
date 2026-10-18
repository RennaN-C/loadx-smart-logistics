import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { AlertBanner } from "../components/AlertBanner";
import { useAuth } from "../features/auth/hooks/useAuth";
import { hasPermission } from "../features/auth/permissions";

/** Projeção das permissões de leitura; o backend continua autorizando cada recurso. */
export function OperationalAccess({ children, overview = false, permission = "loadx.trucks.read", permissions }: { readonly children: ReactNode; readonly overview?: boolean; readonly permission?: string; readonly permissions?: readonly string[] }) {
  const { user } = useAuth();
  const allowed = user?.active && (overview ? hasPermission(user, "loadx.reports.read") : (permissions ?? [permission]).every((code) => hasPermission(user, code)));
  if (!allowed) return <div className="entity-page"><h1>Acesso negado</h1><AlertBanner>Seu perfil não tem permissão para consultar esta área.</AlertBanner><Link to="/">Voltar à visão geral</Link></div>;
  return children;
}
