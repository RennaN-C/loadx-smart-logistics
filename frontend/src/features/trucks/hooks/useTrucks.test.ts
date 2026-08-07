import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import type { Page } from "../../../types/api";
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

function makePage(items: Truck[], page = 1, totalPages = 1): Page<Truck> {
  return {
    items,
    page,
    pageSize: 20,
    total: totalPages === 0 ? 0 : totalPages * 20,
    totalPages,
  };
}

describe("useTrucks", () => {
  beforeEach(() => {
    vi.mocked(listTrucks).mockReset();
  });

  it("carrega a lista ao montar", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage([TRUCK]));

    const { result } = renderHook(() => useTrucks());

    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.trucks).toEqual([TRUCK]);
    expect(result.current.page).toBe(1);
    expect(result.current.totalPages).toBe(1);
    expect(result.current.error).toBeNull();
    expect(listTrucks).toHaveBeenCalledWith({ page: 1, pageSize: 20 });
  });

  it("guarda o ApiError quando a busca falha", async () => {
    vi.mocked(listTrucks).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado."));

    const { result } = renderHook(() => useTrucks());

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error?.code).toBe("AUTH_FORBIDDEN");
    expect(result.current.trucks).toEqual([]);
  });

  it("refetch busca a lista de novo", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage([], 1, 0));

    const { result } = renderHook(() => useTrucks());
    await waitFor(() => expect(result.current.status).toBe("success"));

    vi.mocked(listTrucks).mockResolvedValue(makePage([TRUCK]));
    await result.current.refetch();

    await waitFor(() => expect(result.current.trucks).toEqual([TRUCK]));
    expect(listTrucks).toHaveBeenCalledTimes(2);
  });

  it("carrega a página solicitada", async () => {
    vi.mocked(listTrucks)
      .mockResolvedValueOnce(makePage([TRUCK], 1, 2))
      .mockResolvedValueOnce(makePage([], 2, 2));

    const { result } = renderHook(() => useTrucks());
    await waitFor(() => expect(result.current.status).toBe("success"));

    act(() => result.current.goToPage(2));

    await waitFor(() => expect(result.current.page).toBe(2));
    expect(listTrucks).toHaveBeenLastCalledWith({ page: 2, pageSize: 20 });
  });
});
