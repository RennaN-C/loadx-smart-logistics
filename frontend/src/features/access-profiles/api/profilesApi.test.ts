import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { getProfile, listProfiles, permissionCatalog, saveProfile, type AccessProfile } from "./profilesApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
const INPUT = { name: "Consulta de frota", description: "", active: true, permissions: ["loadx.trucks.read"] };
const PROFILE: AccessProfile = { ...INPUT, id: "p1", system_role: null, version: 3, user_count: 1 };
describe("contrato de perfis OC112", () => {
  beforeEach(() => vi.resetAllMocks());
  it("consulta página e catálogo protegidos", async () => { vi.mocked(api.get).mockResolvedValueOnce({ data: { items: [PROFILE], page: 2, page_size: 20, total: 21, total_pages: 2 } }).mockResolvedValueOnce({ data: [] }); expect((await listProfiles({ page: 2 })).items).toEqual([PROFILE]); expect(api.get).toHaveBeenCalledWith("/access-profiles", { params: expect.objectContaining({ page: 2 }) }); await permissionCatalog(); expect(api.get).toHaveBeenLastCalledWith("/access-profiles/permissions"); });
  it("cria e atualiza usando a versão observada", async () => { vi.mocked(api.post).mockResolvedValue({ data: PROFILE }); vi.mocked(api.patch).mockResolvedValue({ data: PROFILE }); await saveProfile(INPUT); expect(api.post).toHaveBeenCalledWith("/access-profiles", INPUT); await saveProfile(INPUT, PROFILE); expect(api.patch).toHaveBeenCalledWith("/access-profiles/p1", { ...INPUT, version: 3 }); });
  it("consulta detalhe persistido", async () => { vi.mocked(api.get).mockResolvedValue({ data: PROFILE }); expect(await getProfile("p1")).toEqual(PROFILE); });
});
