import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ListParams } from "../services/pagination";
import { makePage } from "../tests/makePage";
import { useRegistryList } from "./useRegistryList";

interface RegistryItem { id: string; active: boolean }

describe("useRegistryList", () => {
  it("consulta ativos por padrão e reinicia paginação ao consultar arquivados", async () => {
    const load = vi.fn(async (params: ListParams) => makePage<RegistryItem>([{ id: "record", active: params.archiveStatus !== "archived" }], params.page ?? 1, 2));
    const { result } = renderHook(() => useRegistryList(load));
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(load).toHaveBeenLastCalledWith({ page: 1, pageSize: 20, archiveStatus: "active" });
    act(() => result.current.goToPage(2));
    await waitFor(() => expect(result.current.page).toBe(2));
    act(() => result.current.setArchiveStatus("archived"));
    await waitFor(() => expect(result.current.items[0]?.active).toBe(false));
    expect(result.current.page).toBe(1);
    expect(load).toHaveBeenLastCalledWith({ page: 1, pageSize: 20, archiveStatus: "archived" });
    act(() => result.current.setArchiveStatus("all"));
    await waitFor(() => expect(load).toHaveBeenLastCalledWith({ page: 1, pageSize: 20, archiveStatus: "all" }));
  });

  it("descarta resposta atrasada do filtro anterior", async () => {
    let resolveOld!: (page: ReturnType<typeof makePage<RegistryItem>>) => void;
    const oldPage = new Promise<ReturnType<typeof makePage<RegistryItem>>>((resolve) => { resolveOld = resolve; });
    const load = vi.fn().mockReturnValueOnce(oldPage).mockResolvedValue(makePage([{ id: "archived", active: false }]));
    const { result } = renderHook(() => useRegistryList<RegistryItem>(load));
    act(() => result.current.setArchiveStatus("archived"));
    await waitFor(() => expect(result.current.items[0]?.id).toBe("archived"));
    await act(async () => resolveOld(makePage([{ id: "active", active: true }])));
    expect(result.current.items[0]?.id).toBe("archived");
  });
});
