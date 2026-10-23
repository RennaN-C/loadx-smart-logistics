import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../types/api";
import { optimizeDistribution, recoverOptimization } from "./api/distributionsApi";
import { makeDistribution } from "./testing/distributionFixtures";
import { useOptimizationRecovery } from "./useOptimizationRecovery";

vi.mock("./api/distributionsApi", async (importOriginal) => ({ ...await importOriginal<typeof import("./api/distributionsApi")>(), optimizeDistribution: vi.fn(), recoverOptimization: vi.fn() }));
const storedKey = "loadx:optimization-request:v1:actor-1";
beforeEach(() => { vi.restoreAllMocks(); vi.resetAllMocks(); sessionStorage.clear(); });
describe("recuperação idempotente", () => {
  it("não envia ao montar; perde resposta, consulta resultado salvo e não cria outra operação", async () => {
    vi.mocked(optimizeDistribution).mockRejectedValue(new ApiError("NETWORK_ERROR", "Conexão interrompida"));
    vi.mocked(recoverOptimization).mockResolvedValue(makeDistribution());
    const onResult = vi.fn();
    const { result } = renderHook(() => useOptimizationRecovery("actor-1", onResult));
    expect(optimizeDistribution).not.toHaveBeenCalled();
    await act(() => result.current.start(["order-1"]));
    const key = result.current.request!.key;
    expect(optimizeDistribution).toHaveBeenCalledWith(["order-1"], key);
    expect(JSON.parse(sessionStorage.getItem(storedKey)!)).toEqual({ key, orderIds: ["order-1"] });
    await act(() => result.current.consult());
    expect(recoverOptimization).toHaveBeenCalledWith(key);
    expect(optimizeDistribution).toHaveBeenCalledTimes(1);
    expect(onResult).toHaveBeenCalledWith(makeDistribution());
    expect(result.current.request).toBeNull();
    expect(sessionStorage.getItem(storedKey)).toBeNull();
  });
  it("após F5 conserva identidade e seleção, sem repetir até ação explícita", async () => {
    vi.mocked(optimizeDistribution).mockRejectedValue(new ApiError("UNKNOWN_ERROR", "Gateway", [], 504));
    const first = renderHook(() => useOptimizationRecovery("actor-1"));
    await act(() => first.result.current.start(["order-1"]));
    const pending = first.result.current.request;
    first.unmount();
    const { result } = renderHook(() => useOptimizationRecovery("actor-1"));
    expect(result.current.request).toEqual(pending);
    expect(optimizeDistribution).toHaveBeenCalledTimes(1);
    await act(() => result.current.start(["other-order"]));
    expect(optimizeDistribution).toHaveBeenCalledTimes(1);
    await act(() => result.current.retry());
    expect(optimizeDistribution).toHaveBeenLastCalledWith(["order-1"], pending!.key);
  });
  it("mantém chave com concorrência e GET 404; não presume rollback", async () => {
    vi.mocked(optimizeDistribution).mockRejectedValue(new ApiError("OPTIMIZATION_IN_PROGRESS", "Em andamento", [], 409));
    vi.mocked(recoverOptimization).mockRejectedValue(new ApiError("OPTIMIZATION_NOT_FOUND", "Não confirmado", [], 404));
    const { result } = renderHook(() => useOptimizationRecovery("actor-1"));
    await act(() => result.current.start(["order-1"]));
    const pending = result.current.request;
    await act(() => result.current.consult());
    expect(result.current.request).toEqual(pending);
  });
  it("expiração da sessão preserva referência para o próximo login do mesmo ator", async () => {
    vi.mocked(optimizeDistribution).mockRejectedValue(new ApiError("AUTH_INVALID_TOKEN", "Sessão expirada", [], 401));
    const { result } = renderHook(() => useOptimizationRecovery("actor-1"));
    await act(() => result.current.start(["order-1"]));
    expect(result.current.request).not.toBeNull();
    expect(sessionStorage.getItem(storedKey)).not.toBeNull();
  });
  it("rejeição definitiva desfaz apenas a referência local", async () => {
    vi.mocked(optimizeDistribution).mockRejectedValue(new ApiError("DISTRIBUTION_CAPACITY_INSUFFICIENT", "Capacidade", [], 422));
    const { result } = renderHook(() => useOptimizationRecovery("actor-1"));
    await act(() => result.current.start(["order-1"]));
    expect(result.current.request).toBeNull();
    expect(sessionStorage.getItem(storedKey)).toBeNull();
    expect(result.current.error).toBeInstanceOf(ApiError);
  });
  it("storage indisponível mantém chave em memória sem impedir retry", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.mocked(optimizeDistribution).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "Conexão")).mockResolvedValue(makeDistribution());
    const { result } = renderHook(() => useOptimizationRecovery("actor-1"));
    await act(() => result.current.start(["order-1"]));
    const key = result.current.request!.key;
    await act(() => result.current.retry());
    expect(optimizeDistribution).toHaveBeenLastCalledWith(["order-1"], key);
    expect(result.current.request).toBeNull();
  });
  it("isola o usuário e rejeita metadados inválidos", async () => {
    sessionStorage.setItem(storedKey, '{"key":"invalid","orderIds":["order-1"]}');
    const { result, rerender } = renderHook(({ actor }) => useOptimizationRecovery(actor), { initialProps: { actor: "actor-1" } });
    expect(result.current.request).toBeNull();
    vi.mocked(optimizeDistribution).mockRejectedValue(new ApiError("NETWORK_ERROR", "Conexão"));
    await act(() => result.current.start(["order-1"]));
    rerender({ actor: "actor-2" });
    await waitFor(() => expect(result.current.request).toBeNull());
    expect(sessionStorage.getItem(storedKey)).not.toBeNull();
    expect(recoverOptimization).not.toHaveBeenCalled();
  });
  it("bloqueia cliques simultâneos", async () => {
    let complete!: (value: ReturnType<typeof makeDistribution>) => void;
    vi.mocked(optimizeDistribution).mockReturnValue(new Promise((resolve) => { complete = resolve; }));
    const { result } = renderHook(() => useOptimizationRecovery("actor-1"));
    act(() => { void result.current.start(["order-1"]); void result.current.start(["order-1"]); });
    expect(optimizeDistribution).toHaveBeenCalledTimes(1);
    await act(async () => complete(makeDistribution()));
  });
});
