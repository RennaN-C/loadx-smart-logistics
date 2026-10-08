import { describe, expect, it } from "vitest";

import { mapOrderFromDto } from "./ordersApi";

describe("mapOrderFromDto", () => {
  it("converte o pedido e os itens aninhados para camelCase", () => {
    expect(
      mapOrderFromDto({
        id: "o1",
        customer_id: "c1",
        status: "DRAFT",
        priority: "NORMAL",
        delivery_address: "Av. Brasil, 500",
        expected_delivery_at: "2026-08-10T17:30:00Z",
        created_at: "2026-08-01T12:00:00Z",
        items: [{ id: "i1", order_id: "o1", product_id: "p1", quantity: 4, delivery_sequence: 2 }],
      }),
    ).toEqual({
      id: "o1",
      customerId: "c1",
      status: "DRAFT",
      priority: "NORMAL",
      deliveryAddress: "Av. Brasil, 500",
      expectedDeliveryAt: "2026-08-10T17:30:00Z",
      createdAt: "2026-08-01T12:00:00Z",
      items: [{ id: "i1", orderId: "o1", productId: "p1", quantity: 4, deliverySequence: 2 }],
    });
  });

  it("preserva previsão de entrega nula", () => {
    const order = mapOrderFromDto({
      id: "o1",
      customer_id: "c1",
      status: "READY",
      priority: "HIGH",
      delivery_address: "Rua A, 1",
      expected_delivery_at: null,
      created_at: "2026-08-01T12:00:00Z",
      items: [],
    });

    expect(order.expectedDeliveryAt).toBeNull();
  });
});

it("preserva proveniência e snapshot retornados pelo backend OC99", () => {
  const snapshot = { address: "Destino contratado", city: "Campinas", customer_address_id: "a1" };
  const order = mapOrderFromDto({ id: "o1", customer_id: "c1", status: "DRAFT", priority: "NORMAL", delivery_address: "Destino contratado", customer_address_id: "a1", delivery_address_snapshot: snapshot, expected_delivery_at: null, created_at: "2026-10-08T00:00:00Z", items: [] });
  expect(order.customerAddressId).toBe("a1");
  expect(order.deliveryAddressSnapshot).toEqual(snapshot);
  expect(order.deliveryAddress).toBe("Destino contratado");
});
