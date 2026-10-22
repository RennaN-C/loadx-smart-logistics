import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { requestProtectedBlob } from "../../../services/protectedDownload";
import { downloadDeliveryEvidence, getDeliveryReceipt, listDeliveryEvidences, registerDeliveryEvidence, revokeDeliveryEvidence } from "./evidencesApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
vi.mock("../../../services/protectedDownload", () => ({ requestProtectedBlob: vi.fn() }));
const EVIDENCE = { id: "e1", delivery_id: "d1", receipt_id: "r1", kind: "PHOTO", media_type: "image/png", size_bytes: 100, sha256: "digest", status: "ACTIVE", recorded_by: "u1", recorded_at: "2026-10-21T12:00:00Z", revoked_by: null, revoked_at: null };
beforeEach(() => vi.resetAllMocks());
describe("Contratos OC78/80 usados na OC81", () => {
  it("consulta comprovante e preserva autoria e identidade sem efetuar conclusão", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { id: "r1", delivery_id: "d1", trip_id: "t1", order_id: "o1", driver_id: "driver", delivered_at: "now", recorded_at: "then", recorded_by: "u1" } });
    expect(await getDeliveryReceipt("d1")).toMatchObject({ deliveryId: "d1", recordedBy: "u1", recordedAt: "then", deliveredAt: "now" });
    expect(api.get).toHaveBeenCalledWith("/deliveries/d1/receipt");
    expect(api.post).not.toHaveBeenCalled();
  });
  it("preserva paginação, tipo e metadados sem procurar bytes ou storage direto", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [EVIDENCE], page: 2, page_size: 20, total: 21, total_pages: 2 } });
    const result = await listDeliveryEvidences("d1", { page: 2, pageSize: 20 });
    expect(result).toMatchObject({ page: 2, total: 21, totalPages: 2, items: [{ deliveryId: "d1", receiptId: "r1", recordedBy: "u1", status: "ACTIVE" }] });
    expect(api.get).toHaveBeenCalledWith("/deliveries/d1/evidences", { params: { page: 2, page_size: 20, sort_order: "desc" } });
  });
  it("reenvia somente a intenção original e não inventa ator, MIME ou caminho", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: EVIDENCE });
    const input = { eventId: "intencao", kind: "PHOTO" as const, contentBase64: "cGl4ZWxz" };
    await registerDeliveryEvidence("d1", input); await registerDeliveryEvidence("d1", input);
    expect(api.post).toHaveBeenCalledWith("/deliveries/d1/evidences", { event_id: "intencao", kind: "PHOTO", content_base64: "cGl4ZWxz" });
    expect(vi.mocked(api.post).mock.calls[1]).toEqual(vi.mocked(api.post).mock.calls[0]);
  });
  it("revoga pelo contrato idempotente e baixa exclusivamente pela API autenticada", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { ...EVIDENCE, status: "REVOKED" } });
    expect(await revokeDeliveryEvidence("d1", "e1")).toMatchObject({ status: "REVOKED" });
    expect(api.post).toHaveBeenCalledWith("/deliveries/d1/evidences/e1/revoke", {});
    const blob = new Blob(["pixels"]); vi.mocked(requestProtectedBlob).mockResolvedValue(blob);
    expect(await downloadDeliveryEvidence("d1", "e1")).toBe(blob);
    expect(requestProtectedBlob).toHaveBeenCalledWith("/deliveries/d1/evidences/e1/content", expect.any(String));
  });
});
