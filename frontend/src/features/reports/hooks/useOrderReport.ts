import { useCallback, useEffect, useState } from "react";

import { MAX_PAGE_SIZE } from "../../../services/pagination";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import type { OrderListItem } from "../../orders/types";
import { buildOrderReport, type OrderReport } from "../reportMetrics";

/**
 * Teto de páginas. O relatório precisa das LINHAS, não só do `total`, e sem
 * filtro server-side (D12) a única saída é paginar a coleção inteira. Mil
 * pedidos é folgado para o MVP; passando disso a tela avisa em vez de mostrar
 * número truncado como se fosse o total.
 */
const MAX_PAGES = 10;

export interface UseOrderReportResult {
  readonly status: "loading" | "ready" | "error";
  readonly report: OrderReport | null;
  /** id do cliente -> nome. Vazio quando o perfil não lê dados pessoais. */
  readonly customerNames: Map<string, string>;
  /** Quantos pedidos ficaram fora por causa do teto de páginas. */
  readonly notCounted: number;
  readonly reference: Date;
  readonly reload: () => void;
}

async function fetchAllOrders(): Promise<{ orders: OrderListItem[]; notCounted: number }> {
  const first = await listOrders({ page: 1, pageSize: MAX_PAGE_SIZE, sortOrder: "desc" });
  const orders = [...first.items];
  const pages = Math.min(first.totalPages, MAX_PAGES);

  for (let page = 2; page <= pages; page += 1) {
    const next = await listOrders({ page, pageSize: MAX_PAGE_SIZE, sortOrder: "desc" });
    orders.push(...next.items);
  }

  return { orders, notCounted: Math.max(0, first.total - orders.length) };
}

/** Nomes para o relatório por cliente. CHECKER não lê clientes: devolve vazio. */
async function fetchCustomerNames(): Promise<Map<string, string>> {
  const names = new Map<string, string>();
  try {
    const first = await listCustomers({ page: 1, pageSize: MAX_PAGE_SIZE });
    const pages = Math.min(first.totalPages, MAX_PAGES);
    for (const customer of first.items) names.set(customer.id, customer.name);

    for (let page = 2; page <= pages; page += 1) {
      const next = await listCustomers({ page, pageSize: MAX_PAGE_SIZE });
      for (const customer of next.items) names.set(customer.id, customer.name);
    }
  } catch {
    // 403 do conferente não pode derrubar o relatório inteiro
    return new Map();
  }
  return names;
}

export function useOrderReport(): UseOrderReportResult {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [report, setReport] = useState<OrderReport | null>(null);
  const [customerNames, setCustomerNames] = useState(new Map<string, string>());
  const [notCounted, setNotCounted] = useState(0);
  // Congelada por carga: com `new Date()` solto no render, "atrasado" mudaria
  // durante a leitura da tela e a contagem deixaria de bater com a lista.
  const [reference, setReference] = useState(() => new Date());

  const load = useCallback(async () => {
    setStatus("loading");
    const agora = new Date();

    try {
      const [{ orders, notCounted: fora }, names] = await Promise.all([
        fetchAllOrders(),
        fetchCustomerNames(),
      ]);

      setReference(agora);
      setReport(buildOrderReport(orders, agora));
      setCustomerNames(names);
      setNotCounted(fora);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { status, report, customerNames, notCounted, reference, reload: () => void load() };
}
