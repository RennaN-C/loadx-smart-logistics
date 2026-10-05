import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../../services/api";
import {
  changeLoadingStatus,
  checkLoadingItem,
  createLoadingSession,
  getLoadingSession,
  scanLoadingItem,
} from "./loadingApi";

vi.mock("../../../services/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}));

const CODE = "loadx:loading-item:11111111-1111-4111-8111-111111111111";

const DTO = {
  id: "ls1",
  load_plan_id: "lp1",
  status: "IN_PROGRESS",
  started_at: "2026-10-05T10:00:00Z",
  finished_at: null,
  items: [{ id: "i1", load_plan_item_id: "pi1", status: "PENDING", code: CODE }],
};

beforeEach(() => {
  vi.mocked(api.get).mockReset().mockResolvedValue({ data: DTO });
  vi.mocked(api.post).mockReset().mockResolvedValue({ data: DTO });
  vi.mocked(api.patch).mockReset().mockResolvedValue({ data: DTO });
});

describe("loadingApi", () => {
  it("traduz snake_case do backend, inclusive dentro dos itens", async () => {
    const session = await getLoadingSession("ls1");

    expect(session).toEqual({
      id: "ls1",
      loadPlanId: "lp1",
      status: "IN_PROGRESS",
      startedAt: "2026-10-05T10:00:00Z",
      finishedAt: null,
      items: [{ id: "i1", loadPlanItemId: "pi1", status: "PENDING", code: CODE }],
    });
  });

  it("cria a sessão a partir do plano", async () => {
    await createLoadingSession("lp1");

    expect(vi.mocked(api.post).mock.calls[0]).toEqual([
      "/loading-sessions",
      { load_plan_id: "lp1" },
    ]);
  });

  it("manda o código EXATAMENTE como foi lido", async () => {
    // O frontend não extrai o UUID nem remonta o texto: quem decide qual item
    // o código identifica é o backend. Reconstruir aqui abriria espaço para a
    // tela marcar um volume que o servidor recusaria.
    await scanLoadingItem("ls1", CODE);

    expect(vi.mocked(api.post).mock.calls[0]).toEqual([
      "/loading-sessions/ls1/scan",
      { code: CODE },
    ]);
  });

  it("confere item pelo endpoint de item, com CHECKED", async () => {
    await checkLoadingItem("ls1", "i1");

    expect(vi.mocked(api.patch).mock.calls[0]).toEqual([
      "/loading-sessions/ls1/items/i1",
      { status: "CHECKED" },
    ]);
  });

  it("muda a etapa pelo endpoint de status", async () => {
    await changeLoadingStatus("ls1", "FINISHED");

    expect(vi.mocked(api.patch).mock.calls[0]).toEqual([
      "/loading-sessions/ls1/status",
      { status: "FINISHED" },
    ]);
  });

  it("toda ação devolve a sessão inteira, que é o que o contrato promete", async () => {
    // A tela se apoia nisso: nenhum contador é derivado no cliente, todos saem
    // da lista que o backend recalculou.
    for (const chamada of [
      () => scanLoadingItem("ls1", CODE),
      () => checkLoadingItem("ls1", "i1"),
      () => changeLoadingStatus("ls1", "FINISHED"),
    ]) {
      await expect(chamada()).resolves.toMatchObject({ id: "ls1", items: expect.any(Array) });
    }
  });
});
