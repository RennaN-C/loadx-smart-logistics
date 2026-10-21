import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { getOutboxAttempts, getOutboxEvent, getOutboxSource, getOutboxSummary, listOutbox, retryOutbox } from "./outboxApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());
describe("OC109: contratos reais da fila", () => {
  it("mapeia paginação e envia filtros e cancelamento", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [], page: 2, page_size: 20, total: 21, total_pages: 2 } });
    const signal = new AbortController().signal;
    const filters = { page: 2, status: "UNCERTAIN" as const, sort_order: "asc" as const };
    expect(await listOutbox(filters, signal)).toEqual({ items: [], page: 2, pageSize: 20, total: 21, totalPages: 2 });
    expect(api.get).toHaveBeenCalledWith("/outbox-events", { params: filters, signal, timeout: 8000 });
  });
  it("usa endpoints de resumo detalhe e histórico paginado", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [], page: 1, page_size: 10, total: 0, total_pages: 0 } });
    await getOutboxSummary(); await getOutboxEvent("a/b"); await getOutboxAttempts("a/b", 1);
    expect(api.get).toHaveBeenNthCalledWith(1, "/outbox-events/summary", expect.any(Object));
    expect(api.get).toHaveBeenNthCalledWith(2, "/outbox-events/a%2Fb", expect.any(Object));
    expect(api.get).toHaveBeenNthCalledWith(3, "/outbox-events/a%2Fb/attempts", { params: { page: 1, page_size: 10 }, signal: undefined, timeout: 8000 });
  });
  it("reprocessa com comando idempotente e revalida origem no servidor", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { status: "PENDING" } });
    vi.mocked(api.get).mockResolvedValue({ data: { href: "/trips/origem" } });
    await retryOutbox("id", "command");
    expect(api.post).toHaveBeenCalledWith("/outbox-events/id/retry", { command_id: "command" }, { timeout: 8000 });
    expect(await getOutboxSource("id")).toBe("/trips/origem");
  });
});
