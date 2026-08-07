import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../types/api";
import { useResourceList } from "./useResourceList";

describe("useResourceList", () => {
  it("carrega a lista ao montar", async () => {
    const load = vi.fn().mockResolvedValue([{ id: "1" }]);

    const { result } = renderHook(() => useResourceList(load));

    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.items).toEqual([{ id: "1" }]);
    expect(result.current.error).toBeNull();
  });

  it("guarda o ApiError quando a busca falha", async () => {
    const load = vi.fn().mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado."));

    const { result } = renderHook(() => useResourceList(load));

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error?.code).toBe("AUTH_FORBIDDEN");
    expect(result.current.items).toEqual([]);
  });

  it("normaliza erro inesperado para ApiError", async () => {
    const load = vi.fn().mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useResourceList(load));

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error?.code).toBe("UNKNOWN_ERROR");
  });

  it("refetch busca a lista de novo", async () => {
    const load = vi.fn().mockResolvedValue([]);

    const { result } = renderHook(() => useResourceList(load));
    await waitFor(() => expect(result.current.status).toBe("success"));

    load.mockResolvedValue([{ id: "2" }]);
    await result.current.refetch();

    await waitFor(() => expect(result.current.items).toEqual([{ id: "2" }]));
    expect(load).toHaveBeenCalledTimes(2);
  });
});
