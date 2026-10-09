import { beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { confirmImport, downloadImportTemplate, getImport, listImports, previewImport, readCsvFile } from "./importsApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn(), notifyIfSessionInvalidated: vi.fn() }, notifyIfSessionInvalidated: vi.fn() }));
const file = { file_name: "fixture.csv", content_base64: "Y3N2" };
beforeEach(() => vi.clearAllMocks());
it.each(["customers", "products", "trucks", "drivers"] as const)("prévia usa fluxo separado de %s", async (entity) => {
  vi.mocked(api.post).mockResolvedValue({ data: { can_confirm: true } });
  await previewImport(entity, file);
  expect(api.post).toHaveBeenCalledWith(`/registration-imports/${entity}/preview`, file);
});
it("confirma com hash e identidade estável sem ator enviado pelo cliente", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { id: "i1" } });
  await confirmImport("products", file, "hash", "event");
  expect(api.post).toHaveBeenCalledWith("/registration-imports/products/confirm", { ...file, preview_sha256: "hash", event_id: "event" });
});
it("consulta histórico filtrado e resultado por identidade", async () => {
  vi.mocked(api.get).mockResolvedValueOnce({ data: { items: [{ id: "i1" }], page: 2, page_size: 20, total: 22, total_pages: 2 } }).mockResolvedValueOnce({ data: { id: "i1", records: [] } });
  expect((await listImports("customers", { page: 2 })).items[0].id).toBe("i1");
  expect(api.get).toHaveBeenCalledWith("/registration-imports", { params: { page: 2, page_size: 20, sort_order: "desc", entity_type: "customers" } });
  expect((await getImport("i1")).id).toBe("i1");
});
it("modelo CSV é baixado com sessão pelo helper protegido", async () => {
  const blob = new Blob(["name,document"]);
  vi.mocked(api.get).mockResolvedValue({ status: 200, data: blob });
  expect(await downloadImportTemplate("drivers")).toBe(blob);
  expect(api.get).toHaveBeenCalledWith("/registration-imports/drivers/template", expect.objectContaining({ responseType: "blob" }));
});
it("lê CSV sem executar conteúdo e rejeita extensão/tamanho", async () => {
  expect(await readCsvFile(new File(["code,name"], "fixture.csv", { type: "text/csv" }))).toEqual({ file_name: "fixture.csv", content_base64: btoa("code,name") });
  for (const candidate of [new File(["xlsx"], "file.xlsx"), new File([], "empty.csv"), new File([new Uint8Array(1048577)], "large.csv")]) {
    await expect(readCsvFile(candidate)).rejects.toThrow("CSV UTF-8");
  }
});
