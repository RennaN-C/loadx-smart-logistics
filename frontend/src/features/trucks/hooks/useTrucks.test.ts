import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { listTrucks } from "../api/trucksApi";
import type { Truck } from "../types";
import { useTrucks } from "./useTrucks";

vi.mock("../api/trucksApi");

const TRUCK: Truck = {
  id: "22222222-2222-2222-2222-222222222222",
  plate: "ABC1D23",
  model: "Baú médio",
  internalWidthCm: 240,
  internalHeightCm: 260,
  internalLengthCm: 600,
  maxWeightKg: 8000,
  active: true,
  createdAt: "2026-08-01T12:00:00Z",
};

describe("useTrucks", () => {
  beforeEach(() => {
    vi.mocked(listTrucks).mockReset();
  });

  it("carrega a lista ao montar", async () => {
    vi.mocked(listTrucks).mockResolvedValue([TRUCK]);

    const { result } = renderHook(() => useTrucks());

    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.trucks).toEqual([TRUCK]);
    expect(result.current.error).toBeNull();
  });

  it("guarda o ApiError quando a busca falha", async () => {
    vi.mocked(listTrucks).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado."));

    const { result } = renderHook(() => useTrucks());

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error?.code).toBe("AUTH_FORBIDDEN");
    expect(result.current.trucks).toEqual([]);
  });

  it("refetch busca a lista de novo", async () => {
    vi.mocked(listTrucks).mockResolvedValue([]);

    const { result } = renderHook(() => useTrucks());
    await waitFor(() => expect(result.current.status).toBe("success"));

    vi.mocked(listTrucks).mockResolvedValue([TRUCK]);
    await result.current.refetch();

    await waitFor(() => expect(result.current.trucks).toEqual([TRUCK]));
    expect(listTrucks).toHaveBeenCalledTimes(2);
  });
});
