import { beforeEach, expect, it, vi } from "vitest";
import { api, notifyIfSessionInvalidated } from "../../../services/api";
import { downloadAttachment, listAttachments, listTripAttachmentOccurrences, readAttachmentFile, revokeAttachment, uploadAttachment } from "./attachmentsApi";

vi.mock("../../../services/api", () => ({ notifyIfSessionInvalidated: vi.fn(), api: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.clearAllMocks());
it("consulta metadata paginada sem endereço público", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { items: [{ id: "a1", status: "ACTIVE" }], page: 2, page_size: 20, total: 22, total_pages: 2 } });
  expect((await listAttachments("orders", "o1", { page: 2 })).items[0].id).toBe("a1");
  expect(api.get).toHaveBeenCalledWith("/attachments/orders/o1", { params: { page: 2, page_size: 20, sort_order: "desc" } });
});
it("envia identidade estável e remove logicamente", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { id: "a1" } });
  await uploadAttachment("deliveries", "d1", "event1", "bytes");
  expect(api.post).toHaveBeenCalledWith("/attachments/deliveries/d1", { event_id: "event1", content_base64: "bytes" });
  await revokeAttachment("deliveries", "d1", "a1");
  expect(api.post).toHaveBeenCalledWith("/attachments/deliveries/d1/a1/revoke", {});
});
it("download usa sessão sem URL pública e preserva erro JSON no blob", async () => {
  const data = new Blob(["image"]);
  vi.mocked(api.get).mockResolvedValueOnce({ status: 200, data });
  expect(await downloadAttachment("trips", "t1", "a1")).toBe(data);
  expect(api.get).toHaveBeenCalledWith("/attachments/trips/t1/a1/content", expect.objectContaining({ responseType: "blob", validateStatus: expect.any(Function) }));
  const errorBlob = new Blob([]);
  Object.defineProperty(errorBlob, "text", { value: async () => JSON.stringify({ code: "ATTACHMENT_REVOKED", message: "Removido", details: [] }) });
  vi.mocked(api.get).mockResolvedValueOnce({ status: 409, data: errorBlob });
  await expect(downloadAttachment("trips", "t1", "a1")).rejects.toMatchObject({ code: "ATTACHMENT_REVOKED" });
});
it("consulta ocorrências pelo contrato existente", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: [{ id: "oc1" }] });
  expect(await listTripAttachmentOccurrences("t1")).toHaveLength(1);
  expect(api.get).toHaveBeenCalledWith("/trips/t1/occurrences");
});
it("lê PNG como base64 e rejeita tamanho ou tipo inválido", async () => {
  expect(await readAttachmentFile(new File(["pixels"], "foto.png", { type: "image/png" }))).toBe(btoa("pixels"));
  for (const file of [new File(["pdf"], "a.pdf", { type: "application/pdf" }), new File([], "empty.png", { type: "image/png" }), new File([new Uint8Array(5242881)], "large.png", { type: "image/png" })]) {
    await expect(readAttachmentFile(file)).rejects.toThrow("PNG/JPEG");
  }
});

it("invalida sessão expirada também no download binário", async () => {
  const errorBlob = new Blob([]);
  Object.defineProperty(errorBlob, "text", { value: async () => JSON.stringify({ code: "AUTH_INVALID_TOKEN", message: "Sessão expirada", details: [] }) });
  vi.mocked(api.get).mockResolvedValue({ status: 401, data: errorBlob });
  await expect(downloadAttachment("trips", "t1", "a1")).rejects.toMatchObject({ code: "AUTH_INVALID_TOKEN", status: 401 });
  expect(notifyIfSessionInvalidated).toHaveBeenCalledWith(expect.objectContaining({ code: "AUTH_INVALID_TOKEN" }));
});
