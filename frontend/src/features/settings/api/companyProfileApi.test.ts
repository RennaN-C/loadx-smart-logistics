import { beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { getCompanyProfile, updateCompanyProfile } from "./companyProfileApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), put: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());
it("consulta singleton preservando resposta vazia", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: null });
  expect(await getCompanyProfile()).toBeNull();
  expect(api.get).toHaveBeenCalledWith("/company-profile");
});
it("substitui somente campos públicos no endpoint aprovado", async () => {
  const input = { legal_name: "Empresa", display_name: "Empresa", cnpj: null, phone: null, email: null, logo_reference: null };
  vi.mocked(api.put).mockResolvedValue({ data: { ...input, id: "fixed-id" } });
  expect(await updateCompanyProfile(input)).toEqual({ ...input, id: "fixed-id" });
  expect(api.put).toHaveBeenCalledWith("/company-profile", input);
});
