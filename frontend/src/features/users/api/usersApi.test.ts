import { beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { createUser, getUser, listUsers, updateUser } from "./usersApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
const DTO = { id: "u1", name: "Pessoa", email: "p@example.test", role: "DRIVER", active: true, driver_id: "d1", created_at: "2026-10-16" };
beforeEach(() => vi.resetAllMocks());
it("mantém paginação e filtros públicos sem buscar por e-mail", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { items: [DTO], page: 2, page_size: 20, total: 21, total_pages: 2 } });
  const result = await listUsers({ search: " Pessoa ", role: "DRIVER", active: false, page: 2, sortOrder: "asc" });
  expect(api.get).toHaveBeenCalledWith("/users", { params: { search: "Pessoa", role: "DRIVER", active: false, page: 2, page_size: 20, sort_order: "asc" } }); expect(result.items[0].driverId).toBe("d1"); expect(result.totalPages).toBe(2);
});
it("reutiliza detalhe, criação e patch com driver_id explícito, inclusive null", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: DTO }); vi.mocked(api.post).mockResolvedValue({ data: DTO }); vi.mocked(api.patch).mockResolvedValue({ data: DTO });
  expect((await getUser("u1")).email).toBe(DTO.email);
  await createUser({ name: DTO.name, email: DTO.email, role: "DRIVER", active: true, driverId: "d1", password: "Frase ficticia segura 2026!" }); expect(api.post).toHaveBeenCalledWith("/users", { name: DTO.name, email: DTO.email, role: "DRIVER", active: true, driver_id: "d1", password: "Frase ficticia segura 2026!" });
  await updateUser("u1", { driverId: null }); expect(api.patch).toHaveBeenCalledWith("/users/u1", { driver_id: null }); await updateUser("u1", { name: "Outro" }); expect(api.patch).toHaveBeenLastCalledWith("/users/u1", { name: "Outro" });
});
