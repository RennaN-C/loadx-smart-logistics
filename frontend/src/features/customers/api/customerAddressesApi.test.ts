import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { createCustomerAddress, listActiveCustomerAddresses, listCustomerAddresses, updateCustomerAddress } from "./customerAddressesApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
const dto = { id: "a1", customer_id: "c1", label: "Principal", address: "Rua fictícia", city: "Campinas", state: "SP", postal_code: null, active: true, is_primary: true, created_at: "2026-10-08T00:00:00Z" };
beforeEach(() => vi.clearAllMocks());
describe("contrato de endereços", () => {
  it("filtra ativos por padrão e mapeia a página", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [dto], page: 1, page_size: 20, total: 1, total_pages: 1 } });
    const page = await listCustomerAddresses("c1");
    expect(api.get).toHaveBeenCalledWith("/customers/c1/addresses", { params: expect.objectContaining({ archive_status: "active" }) });
    expect(page.items[0]).toMatchObject({ id: "a1", customerId: "c1", isPrimary: true, postalCode: null });
  });
  it("percorre todas as páginas para seleção operacional", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { items: [dto], page: 1, page_size: 100, total: 2, total_pages: 2 } }).mockResolvedValueOnce({ data: { items: [{ ...dto, id: "a2", active: false }], page: 2, page_size: 100, total: 2, total_pages: 2 } });
    expect((await listActiveCustomerAddresses("c1")).map((a) => a.id)).toEqual(["a1"]);
    expect(api.get).toHaveBeenLastCalledWith("/customers/c1/addresses", { params: expect.objectContaining({ page: 2, archive_status: "active" }) });
  });
  it("cria em snake_case e atualiza somente os campos enviados", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: dto });
    vi.mocked(api.patch).mockResolvedValue({ data: dto });
    await createCustomerAddress("c1", { label: "Principal", address: "Rua", city: "Campinas", state: "SP", postalCode: "13000000", isPrimary: true, active: true });
    expect(api.post).toHaveBeenCalledWith("/customers/c1/addresses", expect.objectContaining({ postal_code: "13000000", is_primary: true }));
    await updateCustomerAddress("c1", "a1", { active: false });
    expect(api.patch).toHaveBeenCalledWith("/customers/c1/addresses/a1", { active: false });
  });
});
