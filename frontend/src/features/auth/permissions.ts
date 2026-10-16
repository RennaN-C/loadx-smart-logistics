import type { AuthenticatedUser, Role } from "./types";

/** UI projection only. Server authorization and resource scope remain authoritative. */
const LOGISTICS_PERMISSIONS: readonly string[] = [
  "loadx.audit.read",
  "loadx.customers.manage",
  "loadx.customers.read",
  "loadx.deliveries.manage",
  "loadx.deliveries.read",
  "loadx.drivers.manage",
  "loadx.drivers.read",
  "loadx.imports.manage",
  "loadx.loading.create",
  "loadx.loading.read",
  "loadx.messages.manage",
  "loadx.occurrences.manage",
  "loadx.occurrences.read",
  "loadx.orders.manage",
  "loadx.orders.read",
  "loadx.planning.approve",
  "loadx.planning.create",
  "loadx.planning.read",
  "loadx.products.manage",
  "loadx.products.read",
  "loadx.reports.read",
  "loadx.trips.manage",
  "loadx.trips.read",
  "loadx.trucks.manage",
  "loadx.trucks.read"
];
const SYSTEM_PERMISSIONS: Partial<Record<Role, readonly string[]>> = {
  ADMIN: [...LOGISTICS_PERMISSIONS, "loadx.integrations.read", "loadx.loading.operate", "loadx.profiles.manage", "loadx.settings.manage", "loadx.users.manage"],
  LOGISTICS_MANAGER: LOGISTICS_PERMISSIONS,
  CHECKER: ["loadx.loading.operate", "loadx.loading.read", "loadx.orders.read", "loadx.planning.read", "loadx.products.read", "loadx.trucks.read"],
  DRIVER: ["loadx.trips.own"],
};
export type PermissionSubject = AuthenticatedUser | Role | null | undefined;
export function hasPermission(subject: PermissionSubject, code: string): boolean {
  if (!subject || (typeof subject !== "string" && !subject.active)) return false;
  const role = typeof subject === "string" ? subject : subject.role;
  const permissions = typeof subject === "string" ? undefined : subject.permissions;
  return (permissions ?? SYSTEM_PERMISSIONS[role] ?? []).includes(code);
}
export function canManageLogistics(subject: PermissionSubject, resource = "customers"): boolean {
  return hasPermission(subject, `loadx.${resource}.manage`);
}
export function canCheckLoading(subject: PermissionSubject): boolean { return hasPermission(subject, "loadx.loading.operate"); }
export function canOperateTrip(subject: PermissionSubject): boolean { return hasPermission(subject, "loadx.trips.manage") || hasPermission(subject, "loadx.trips.own"); }
