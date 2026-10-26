import { beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { listDocuments, listDocumentPolicies, saveDocument, setDocumentPolicy } from "./documentsApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
const input = { kind: "CRLV" as const, reference: "REF", issued_at: null, expires_at: null, file_reference: null };
beforeEach(() => vi.clearAllMocks());
it("preserva o contrato documental e paginação", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { items: [{ ...input, id: "d1", status: "VALID" }], page: 2, page_size: 10, total: 11, total_pages: 2 } });
  const result = await listDocuments("t1", { page: 2, pageSize: 10 });
  expect(result.items[0]).toMatchObject({ reference: "REF", status: "VALID" });
  expect(result.totalPages).toBe(2);
  expect(api.get).toHaveBeenCalledWith("/trucks/t1/documents", { params: { page: 2, page_size: 10, sort_order: "desc" } });
});
it("cadastra e renova pela identidade estável", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: input });
  await saveDocument("t1", input);
  expect(api.post).toHaveBeenLastCalledWith("/trucks/t1/documents", input);
  await saveDocument("t1", input, "d1");
  expect(api.post).toHaveBeenLastCalledWith("/trucks/t1/documents/d1/renew", input);
});
it("consulta e configura política sem alterar cadastro", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: [] }); vi.mocked(api.patch).mockResolvedValue({ data: { kind: "CRLV", required: true } });
  expect(await listDocumentPolicies("t1")).toEqual([]);
  await setDocumentPolicy("t1", "CRLV", true);
  expect(api.patch).toHaveBeenCalledWith("/trucks/t1/document-policies/CRLV", { required: true });
});
