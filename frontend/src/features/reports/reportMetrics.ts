import type { OrderListItem, OrderStatus } from "../orders/types";

/**
 * Indicadores da OC35, calculados a partir da listagem de pedidos.
 *
 * Não existe endpoint de agregação no backend — o mesmo motivo que levou o
 * dashboard (OC25) a contar pelo `total` do envelope de paginação. Aqui os
 * números exigem as linhas, não só a contagem, então a tela pagina a coleção e
 * agrega aqui.
 *
 * Tudo neste arquivo é função PURA: nenhuma chamada HTTP e nenhum `new Date()`
 * implícito. A data de referência entra por parâmetro, como em
 * `orders/components/orderDateTime.ts`, para o "atrasado" ser testável e não
 * depender do fuso nem do relógio de quem roda o teste.
 */

/** Situações que encerram o pedido: não contam como aberto nem como atrasado. */
const CLOSED: readonly OrderStatus[] = ["DELIVERED", "CANCELED"];

export function isClosed(status: OrderStatus): boolean {
  return CLOSED.includes(status);
}

/**
 * Atrasado é pedido com previsão no passado que ainda não fechou. Pedido sem
 * previsão nunca atrasa: não há prazo para descumprir.
 */
export function isLate(order: OrderListItem, reference: Date): boolean {
  if (order.expectedDeliveryAt === null || isClosed(order.status)) return false;

  return new Date(order.expectedDeliveryAt).getTime() < reference.getTime();
}

export interface Slice {
  readonly key: string;
  readonly count: number;
  /** Fatia do total, de 0 a 1. Usada na largura da barra. */
  readonly share: number;
}

/** Distribuição por chave, já com a fatia calculada e ordenada da maior. */
function distribution(keys: readonly string[]): Slice[] {
  const counts = new Map<string, number>();
  for (const key of keys) counts.set(key, (counts.get(key) ?? 0) + 1);

  return [...counts.entries()]
    .map(([key, count]) => ({ key, count, share: keys.length === 0 ? 0 : count / keys.length }))
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key));
}

export interface CustomerRow {
  readonly customerId: string;
  readonly orders: number;
  readonly volumes: number;
  readonly late: number;
}

export interface OrderReport {
  readonly total: number;
  readonly open: number;
  readonly late: number;
  /** Volumes dos pedidos em aberto: é o que ainda precisa entrar em caminhão. */
  readonly openVolumes: number;
  readonly byStatus: Slice[];
  readonly byPriority: Slice[];
  readonly byCustomer: CustomerRow[];
  readonly lateOrders: OrderListItem[];
}

export function buildOrderReport(orders: readonly OrderListItem[], reference: Date): OrderReport {
  const open = orders.filter((order) => !isClosed(order.status));
  const lateOrders = orders.filter((order) => isLate(order, reference));

  const perCustomer = new Map<string, { orders: number; volumes: number; late: number }>();
  for (const order of orders) {
    const row = perCustomer.get(order.customerId) ?? { orders: 0, volumes: 0, late: 0 };
    row.orders += 1;
    row.volumes += order.itemCount;
    if (isLate(order, reference)) row.late += 1;
    perCustomer.set(order.customerId, row);
  }

  return {
    total: orders.length,
    open: open.length,
    late: lateOrders.length,
    openVolumes: open.reduce((sum, order) => sum + order.itemCount, 0),
    byStatus: distribution(orders.map((order) => order.status)),
    // priority é string livre no backend (docs/11): valor fora da convenção
    // entra pelo rótulo cru, em vez de ser descartado da contagem.
    byPriority: distribution(orders.map((order) => order.priority)),
    byCustomer: [...perCustomer.entries()]
      .map(([customerId, row]) => ({ customerId, ...row }))
      .sort((a, b) => b.volumes - a.volumes || b.orders - a.orders),
    lateOrders: [...lateOrders].sort((a, b) => {
      // mais atrasado primeiro: quem tem a previsão mais antiga
      const left = a.expectedDeliveryAt ?? "";
      const right = b.expectedDeliveryAt ?? "";
      return left.localeCompare(right);
    }),
  };
}
