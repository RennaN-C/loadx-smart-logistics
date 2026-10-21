import { expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { listDeliveryCommunications } from "./communicationsApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn() } }));
it("consulta somente o contrato por entrega com paginação server-side", async () => {
  const row = { id: "fato", occurrence_id: "origem", event_type: "OCCURRENCE_REGISTERED", channel: "WHATSAPP_MOCK", simulation_status: "FAILED", processing_status: "UNCERTAIN", created_at: "2026-10-21T12:00:00Z" };
  vi.mocked(api.get).mockResolvedValue({ data: { items: [row], page: 2, page_size: 20, total: 21, total_pages: 2 } });
  expect(await listDeliveryCommunications("entrega/identificada", { page: 2, pageSize: 20, sortOrder: "asc" })).toEqual({ items: [row], page: 2, pageSize: 20, total: 21, totalPages: 2 });
  expect(api.get).toHaveBeenCalledWith("/deliveries/entrega%2Fidentificada/communications", { params: { page: 2, page_size: 20, sort_order: "asc" } });
});
