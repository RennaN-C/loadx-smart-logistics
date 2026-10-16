import type { IconName } from "../../../components/Icon";
import { hasPermission, type PermissionSubject } from "../../auth/permissions";
import type { Role } from "../../auth/types";
import type { SearchCategory, SearchResult } from "../api/searchApi";

export const CATEGORIES: Record<SearchCategory, { label: string; icon: IconName; path: string }> = {
  order: { label: "Pedidos", icon: "orders", path: "/orders?" },
  customer: { label: "Clientes", icon: "users", path: "/contacts?" },
  truck: { label: "Caminhões", icon: "truck", path: "/trucks?" },
  driver: { label: "Motoristas", icon: "users", path: "/contacts?" },
  trip: { label: "Viagens", icon: "truck", path: "/trips/" },
};

const ALL_CATEGORIES = Object.keys(CATEGORIES);
const ALLOWED_CATEGORIES: Record<Role, readonly string[]> = {
  ADMIN: ALL_CATEGORIES,
  LOGISTICS_MANAGER: ALL_CATEGORIES,
  CHECKER: ["order", "truck"],
  DRIVER: ["trip"],
  CUSTOM: [],
};

/** Defesa de apresentação; não substitui o RBAC e o escopo de vínculo da API. */
export function visibleResults(items: SearchResult[], user: PermissionSubject) {
  const role = typeof user === "string" ? user : user?.role;
  let allowed = role ? ALLOWED_CATEGORIES[role] : [];
  if (role === "CUSTOM") allowed = ALL_CATEGORIES.filter((category) => hasPermission(user, `loadx.${({ order: "orders", customer: "customers", truck: "trucks", driver: "drivers", trip: "trips" } as Record<string, string>)[category]}.read`));
  return items.filter((item) => allowed.includes(item.category) && item.href.startsWith(CATEGORIES[item.category].path))
    .sort((a, b) => ALL_CATEGORIES.indexOf(a.category) - ALL_CATEGORIES.indexOf(b.category));
}
