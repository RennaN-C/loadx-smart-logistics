import { describe, expect, it } from "vitest";

import type { OrderListItem, OrderStatus } from "../orders/types";
import { buildOrderReport, isClosed, isLate } from "./reportMetrics";

const REFERENCE = new Date("2026-08-20T12:00:00Z");

function order(overrides: Partial<OrderListItem> = {}): OrderListItem {
  return {
    id: crypto.randomUUID(),
    customerId: "c1",
    status: "READY",
    priority: "NORMAL",
    expectedDeliveryAt: null,
    createdAt: "2026-08-01T00:00:00Z",
    itemCount: 1,
    ...overrides,
  };
}

describe("isClosed", () => {
  it("encerra em entregue e cancelado, e só neles", () => {
    const fechados: OrderStatus[] = ["DELIVERED", "CANCELED"];
    const abertos: OrderStatus[] = ["DRAFT", "READY", "PLANNED", "IN_TRANSIT"];

    for (const status of fechados) expect(isClosed(status)).toBe(true);
    for (const status of abertos) expect(isClosed(status)).toBe(false);
  });
});

describe("isLate", () => {
  it("atrasa quando a previsão já passou e o pedido não fechou", () => {
    expect(isLate(order({ expectedDeliveryAt: "2026-08-19T12:00:00Z" }), REFERENCE)).toBe(true);
  });

  it("não atrasa quando a previsão ainda está no futuro", () => {
    expect(isLate(order({ expectedDeliveryAt: "2026-08-21T12:00:00Z" }), REFERENCE)).toBe(false);
  });

  it("pedido sem previsão nunca atrasa: não há prazo para descumprir", () => {
    expect(isLate(order({ expectedDeliveryAt: null }), REFERENCE)).toBe(false);
  });

  it("não atrasa pedido já entregue nem cancelado, por antiga que seja a previsão", () => {
    const vencido = "2020-01-01T00:00:00Z";

    expect(isLate(order({ expectedDeliveryAt: vencido, status: "DELIVERED" }), REFERENCE)).toBe(false);
    expect(isLate(order({ expectedDeliveryAt: vencido, status: "CANCELED" }), REFERENCE)).toBe(false);
  });

  it("não usa o relógio de quem roda: a referência entra por parâmetro", () => {
    const pedido = order({ expectedDeliveryAt: "2026-08-20T12:00:00Z" });

    expect(isLate(pedido, new Date("2026-08-20T11:59:59Z"))).toBe(false);
    expect(isLate(pedido, new Date("2026-08-20T12:00:01Z"))).toBe(true);
  });
});

describe("buildOrderReport", () => {
  it("conta aberto ignorando entregue e cancelado", () => {
    const report = buildOrderReport(
      [
        order({ status: "DRAFT" }),
        order({ status: "IN_TRANSIT" }),
        order({ status: "DELIVERED" }),
        order({ status: "CANCELED" }),
      ],
      REFERENCE,
    );

    expect(report.total).toBe(4);
    expect(report.open).toBe(2);
  });

  it("soma volumes só dos pedidos em aberto", () => {
    const report = buildOrderReport(
      [
        order({ status: "READY", itemCount: 3 }),
        order({ status: "PLANNED", itemCount: 5 }),
        order({ status: "DELIVERED", itemCount: 100 }),
      ],
      REFERENCE,
    );

    expect(report.openVolumes).toBe(8);
  });

  it("distribui por situação com a fatia somando 1", () => {
    const report = buildOrderReport(
      [order({ status: "READY" }), order({ status: "READY" }), order({ status: "DRAFT" })],
      REFERENCE,
    );

    expect(report.byStatus[0]).toEqual({ key: "READY", count: 2, share: 2 / 3 });
    expect(report.byStatus.reduce((sum, slice) => sum + slice.share, 0)).toBeCloseTo(1, 10);
  });

  it("conta prioridade fora da convenção em vez de descartar", () => {
    // priority é string livre no backend (docs/11)
    const report = buildOrderReport(
      [order({ priority: "NORMAL" }), order({ priority: "IMEDIATA" })],
      REFERENCE,
    );

    expect(report.byPriority.map((slice) => slice.key).sort()).toEqual(["IMEDIATA", "NORMAL"]);
  });

  it("agrupa por cliente e ordena pelo maior volume", () => {
    const report = buildOrderReport(
      [
        order({ customerId: "a", itemCount: 2 }),
        order({ customerId: "b", itemCount: 9 }),
        order({ customerId: "a", itemCount: 3 }),
      ],
      REFERENCE,
    );

    expect(report.byCustomer).toEqual([
      { customerId: "b", orders: 1, volumes: 9, late: 0 },
      { customerId: "a", orders: 2, volumes: 5, late: 0 },
    ]);
  });

  it("lista os atrasados começando pelo mais antigo", () => {
    const report = buildOrderReport(
      [
        order({ id: "recente", expectedDeliveryAt: "2026-08-19T00:00:00Z" }),
        order({ id: "antigo", expectedDeliveryAt: "2026-08-10T00:00:00Z" }),
        order({ id: "no_prazo", expectedDeliveryAt: "2026-09-01T00:00:00Z" }),
      ],
      REFERENCE,
    );

    expect(report.late).toBe(2);
    expect(report.lateOrders.map((o) => o.id)).toEqual(["antigo", "recente"]);
  });

  it("não divide por zero quando não há pedido", () => {
    const report = buildOrderReport([], REFERENCE);

    expect(report).toMatchObject({ total: 0, open: 0, late: 0, openVolumes: 0 });
    expect(report.byStatus).toEqual([]);
    expect(report.byCustomer).toEqual([]);
  });
});
