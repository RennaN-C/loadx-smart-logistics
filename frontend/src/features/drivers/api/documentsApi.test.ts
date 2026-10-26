import { beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { approveDocumentType, listDocuments, listDocumentTypes, saveDocument, setDocumentPolicy } from "./documentsApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
const input = { document_type_id: "cnh", reference: "12345678900", category: "D", issued_at: null, expires_at: "2099-01-01T00:00:00Z" };
beforeEach(() => vi.clearAllMocks());
it("lista tipos aprovados e histórico paginado", async () => {
  vi.mocked(api.get).mockResolvedValueOnce({ data: [{ id: "cnh", code: "CNH", name: "CNH" }] }).mockResolvedValueOnce({ data: { items: [{ ...input, id: "d1", status: "VALID" }], page: 1, page_size: 20, total: 1, total_pages: 1 } });
  expect(await listDocumentTypes()).toHaveLength(1); expect((await listDocuments("m1")).items[0].reference).toBe("12345678900");
});
it("renova por identidade e configura categorias explícitas", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: input }); vi.mocked(api.patch).mockResolvedValue({ data: {} });
  await saveDocument("m1", input, "d1"); expect(api.post).toHaveBeenCalledWith("/drivers/m1/documents/d1/renew", input);
  await setDocumentPolicy("m1", "cnh", true, ["D"]); expect(api.patch).toHaveBeenCalledWith("/drivers/m1/document-policies/cnh", { required: true, allowed_categories: ["D"] });
});
it("aprova somente tipos informados explicitamente", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { id: "t2" } }); await approveDocumentType("LOCAL", "Documento local");
  expect(api.post).toHaveBeenCalledWith("/driver-document-types", { code: "LOCAL", name: "Documento local" });
});
