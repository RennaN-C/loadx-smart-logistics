import type { IconName } from "../../../components/Icon";
import type { Role } from "../../auth/types";
import type { SearchCategory, SearchResult } from "../api/searchApi";

export const CATEGORIES: Record<SearchCategory, { label: string; icon: IconName; path: string }> = {
  order: { label: "Pedidos", icon: "orders", path: "/orders?" },
  customer: { label: "Clientes", icon: "users", path: "/contacts?" },
  truck: { label: "Caminhões", icon: "truck", path: "/trucks?" },
  driver: { label: "Motoristas", icon: "users", path: "/contacts?" },
  trip: { label: "Viagens", icon: "truck", path: "/trips/" },
};

/** Defesa de apresentação; não substitui o RBAC e o escopo de vínculo da API. */
export function visibleResults(items: SearchResult[], role: Role | undefined) {
  const categories = Object.keys(CATEGORIES);
  const allowed = role === "DRIVER" ? ["trip"] : role === "CHECKER" ? ["order", "truck"] : role ? categories : [];
  return items.filter((item) => allowed.includes(item.category) && item.href.startsWith(CATEGORIES[item.category].path))
    .sort((a, b) => categories.indexOf(a.category) - categories.indexOf(b.category));
}
