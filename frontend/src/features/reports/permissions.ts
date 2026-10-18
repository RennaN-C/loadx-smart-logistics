import { hasPermission, type PermissionSubject } from "../auth/permissions";
/** Os indicadores usam a listagem de pedidos: ambos os grants são necessários. */
export function canReadReports(user: PermissionSubject): boolean {
  return hasPermission(user, "loadx.reports.read") && hasPermission(user, "loadx.orders.read");
}
