import type { Role } from "./types";

/**
 * Política fixa da v1.2.0: ADMIN inclui poderes operacionais do gerente.
 * A OC112 evoluirá estas verificações para permissões logísticas efetivas.
 * Esta projeção de UI não substitui autorização e vínculos no backend.
 */
export function canManageLogistics(role: Role | undefined): boolean {
  return role === "ADMIN" || role === "LOGISTICS_MANAGER";
}

export function canCheckLoading(role: Role | undefined): boolean {
  return role === "ADMIN" || role === "CHECKER";
}

export function canOperateTrip(role: Role | undefined): boolean {
  return canManageLogistics(role) || role === "DRIVER";
}
