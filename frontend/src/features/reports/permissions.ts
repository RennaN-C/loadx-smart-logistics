import { hasPermission, type PermissionSubject } from "../auth/permissions";
export function canReadReports(user: PermissionSubject): boolean { return hasPermission(user, "loadx.reports.read"); }
