import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { makePage } from "../tests/makePage";
import { ApiError } from "../types/api";
import { useResourceList } from "./useResourceList";

describe("useResourceList", () => {
  it("carrega a primeira página ao montar", async () => {
    const load = vi.fn().mockResolvedValue(makePage([{ id: "1" }]));

    const { result } = renderHook(() => useResourceList(load));

    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.items).toEqual([{ id: "1" }]);
    expect(load).toHaveBeenCalledWith({ page: 1, pageSize: 20 });
  });

  it("expõe os metadados de paginação do backend", async () => {
    const load = vi.fn().mockResolvedValue(makePage([{ id: "1" }], 2, 3));

    const { result } = renderHook(() => useResourceList(load));

    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.page).toBe(2);
    expect(result.current.totalPages).toBe(3);
    expect(result.current.total).toBe(21);
  });

  it("busca a página pedida em goToPage", async () => {
    const load = vi.fn().mockResolvedValue(makePage([{ id: "1" }], 1, 2));

    const { result } = renderHook(() => useResourceList(load));
    await waitFor(() => expect(result.current.status).toBe("success"));

    result.current.goToPage(2);

    await waitFor(() => expect(load).toHaveBeenLastCalledWith({ page: 2, pageSize: 20 }));
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

  it("refetch busca a mesma página de novo", async () => {
    const load = vi.fn().mockResolvedValue(makePage([]));

    const { result } = renderHook(() => useResourceList(load));
    await waitFor(() => expect(result.current.status).toBe("success"));

    load.mockResolvedValue(makePage([{ id: "2" }]));
    await result.current.refetch();

    await waitFor(() => expect(result.current.items).toEqual([{ id: "2" }]));
    expect(load).toHaveBeenCalledTimes(2);
  });
});
