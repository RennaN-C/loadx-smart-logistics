import { describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { changeOwnPassword, listOwnSessions, revokeOtherSessions, revokeOwnSession, updateOwnProfile } from "./accountApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), patch: vi.fn(), post: vi.fn(), delete: vi.fn() } }));
describe("Contratos OC92", () => {
  it("atualiza somente nome e email e mapeia resposta", async () => { vi.mocked(api.patch).mockResolvedValue({ data: { id: "u1", name: "Nome", email: "a@example.test", role: "CHECKER", active: true, created_at: "2026-10-10" } }); expect((await updateOwnProfile("Nome", "a@example.test")).createdAt).toBe("2026-10-10"); expect(api.patch).toHaveBeenCalledWith("/auth/me", { name: "Nome", email: "a@example.test" }); });
  it("envia confirmação de senha pelo contrato local", async () => { await changeOwnPassword("atual", "nova"); expect(api.post).toHaveBeenCalledWith("/auth/me/password", { current_password: "atual", new_password: "nova" }); });
  it("consulta metadata de sessões", async () => { vi.mocked(api.get).mockResolvedValue({ data: [] }); expect(await listOwnSessions()).toEqual([]); expect(api.get).toHaveBeenCalledWith("/auth/me/sessions"); });
  it("revoga sessão própria identificada e outras", async () => { await revokeOwnSession("id-1"); await revokeOtherSessions(); expect(api.delete).toHaveBeenCalledWith("/auth/me/sessions/id-1"); expect(api.post).toHaveBeenCalledWith("/auth/me/sessions/revoke-others"); });
});
