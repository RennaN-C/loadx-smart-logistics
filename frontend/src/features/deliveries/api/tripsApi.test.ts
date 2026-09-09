import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../../services/api";
import { ApiError } from "../../../types/api";
import { changeDeliveryStatus } from "./tripsApi";

vi.mock("../../../services/api", () => ({ api: { patch: vi.fn(), get: vi.fn() } }));

const DELIVERY_DTO = {
  id: "dl1",
  trip_id: "tp1",
  order_id: "o1",
  status: "IN_DELIVERY",
  sequence: 1,
  delivered_at: null,
};

describe("changeDeliveryStatus", () => {
  beforeEach(() => vi.resetAllMocks());

  it("interpreta DeliveryRead e retorna a viagem autoritativa do GET após o PATCH", async () => {
    vi.mocked(api.patch).mockResolvedValue({ data: DELIVERY_DTO });
    vi.mocked(api.get).mockResolvedValue({
      data: {
        id: "tp1",
        load_plan_id: "lp1",
        driver_id: "d1",
        status: "IN_ROUTE",
        started_at: "2026-09-09T10:00:00Z",
        finished_at: null,
        deliveries: [{ ...DELIVERY_DTO, status: "DELIVERED", delivered_at: "2026-09-09T12:00:00Z" }],
      },
    });

    const trip = await changeDeliveryStatus("dl1", "IN_DELIVERY");

    expect(api.patch).toHaveBeenCalledExactlyOnceWith("/deliveries/dl1/status", { status: "IN_DELIVERY" });
    expect(api.get).toHaveBeenCalledExactlyOnceWith("/trips/tp1");
    expect(vi.mocked(api.patch).mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(api.get).mock.invocationCallOrder[0],
    );
    // O GET pode observar um estado mais recente que o PATCH; ele é a fonte final.
    expect(trip).toEqual({
      id: "tp1",
      loadPlanId: "lp1",
      driverId: "d1",
      status: "IN_ROUTE",
      startedAt: "2026-09-09T10:00:00Z",
      finishedAt: null,
      deliveries: [{
        id: "dl1", tripId: "tp1", orderId: "o1", status: "DELIVERED",
        sequence: 1, deliveredAt: "2026-09-09T12:00:00Z",
      }],
    });
  });

  it("preserva o erro do PATCH e não busca a viagem quando a transição falha", async () => {
    const error = new ApiError("DELIVERY_TRIP_NOT_IN_ROUTE", "Viagem fora de rota.");
    vi.mocked(api.patch).mockRejectedValue(error);

    await expect(changeDeliveryStatus("dl1", "IN_DELIVERY")).rejects.toBe(error);
    expect(api.get).not.toHaveBeenCalled();
  });

  it("propaga falha de recarga sem repetir o PATCH confirmado", async () => {
    const error = new ApiError("TRIP_NOT_FOUND", "Viagem não encontrada.");
    vi.mocked(api.patch).mockResolvedValue({ data: DELIVERY_DTO });
    vi.mocked(api.get).mockRejectedValue(error);

    await expect(changeDeliveryStatus("dl1", "IN_DELIVERY")).rejects.toBe(error);
    expect(api.patch).toHaveBeenCalledTimes(1);
    expect(api.get).toHaveBeenCalledTimes(1);
  });
});
