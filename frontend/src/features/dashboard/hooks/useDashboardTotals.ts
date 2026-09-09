import { useCallback, useEffect, useState } from "react";

import { listCustomers } from "../../customers/api/customersApi";
import { listDrivers } from "../../drivers/api/driversApi";
import { listOrders } from "../../orders/api/ordersApi";
import { listProducts } from "../../products/api/productsApi";
import { listTrucks } from "../../trucks/api/trucksApi";
import type { Role } from "../../auth/types";
import type { OrderListItem } from "../../orders/types";

export interface DashboardTotals {
  trucks: number | null;
  products: number | null;
  customers: number | null;
  drivers: number | null;
  orders: number | null;
}

export interface UseDashboardResult {
  status: "loading" | "ready";
  totals: DashboardTotals;
  recentOrders: OrderListItem[];
  /** Recursos que responderam erro; a tela mostra "—" no lugar do número. */
  unavailable: string[];
}

const EMPTY: DashboardTotals = {
  trucks: null,
  products: null,
  customers: null,
  drivers: null,
  orders: null,
};

/**
 * Não existe endpoint de agregação no backend. Os contadores vêm do `total` do
 * envelope de paginação — pedindo `page_size=1`, o número é exato e a resposta é
 * mínima, sem baixar a coleção inteira só para contar.
 *
 * Cada recurso é buscado de forma independente: `CHECKER` não lê clientes nem
 * motoristas, e um 403 ali não pode derrubar o resto do painel.
 */
export function useDashboardTotals(role: Role | undefined): UseDashboardResult {
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [totals, setTotals] = useState<DashboardTotals>(EMPTY);
  const [recentOrders, setRecentOrders] = useState<OrderListItem[]>([]);
  const [unavailable, setUnavailable] = useState<string[]>([]);

  const readsPersonalData = role === "ADMIN" || role === "LOGISTICS_MANAGER";

  const load = useCallback(async () => {
    setStatus("loading");
    const missing: string[] = [];

    const countOf = async (
      key: string,
      list: (params: { pageSize: number }) => Promise<{ total: number }>,
    ): Promise<number | null> => {
      try {
        return (await list({ pageSize: 1 })).total;
      } catch {
        missing.push(key);
        return null;
      }
    };

    // page_size maior só nos pedidos: além do total, a tela lista os mais recentes
    const ordersPromise = listOrders({ pageSize: 5 })
      .then((page) => page)
      .catch(() => {
        missing.push("orders");
        return null;
      });

    const [trucks, products, customers, drivers, orders] = await Promise.all([
      countOf("trucks", listTrucks),
      countOf("products", listProducts),
      readsPersonalData ? countOf("customers", listCustomers) : Promise.resolve(null),
      readsPersonalData ? countOf("drivers", listDrivers) : Promise.resolve(null),
      ordersPromise,
    ]);

    setTotals({ trucks, products, customers, drivers, orders: orders?.total ?? null });
    setRecentOrders(orders?.items ?? []);
    setUnavailable(missing);
    setStatus("ready");
  }, [readsPersonalData]);

  useEffect(() => {
    void load();
  }, [load]);

  return { status, totals, recentOrders, unavailable };
}
