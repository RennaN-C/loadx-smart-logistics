import { beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { getNotificationPreferences, getNotificationSource, getUnreadCount, listNotifications, markAllNotificationsRead, markNotificationRead, saveNotificationPreferences } from "./notificationsApi";

vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());
it("consome paginação real e o contador do mesmo envelope", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { items: [], page: 2, page_size: 20, total: 25, total_pages: 2, unread_count: 7 } });
  const result = await listNotifications({ page: 2, read: false, category: "TRIPS", sort_order: "asc" });
  expect(api.get).toHaveBeenCalledWith("/notifications", { params: { page: 2, read: false, category: "TRIPS", sort_order: "asc" }, signal: undefined });
  expect(result).toEqual({ items: [], page: 2, pageSize: 20, total: 25, totalPages: 2, unreadCount: 7 });
});
it("não envia destinatário ou data ao marcar leitura", async () => {
  vi.mocked(api.post).mockResolvedValueOnce({ data: { id: "id", read_at: "2026-10-20T10:00:00Z" } }).mockResolvedValueOnce({ data: { updated: 3 } });
  expect((await markNotificationRead("id")).read_at).toBeTruthy();
  expect(await markAllNotificationsRead()).toBe(3);
  expect(api.post).toHaveBeenNthCalledWith(1, "/notifications/id/read");
  expect(api.post).toHaveBeenNthCalledWith(2, "/notifications/read-all");
});
it("consulta contador e origem autorizada pelo servidor", async () => {
  vi.mocked(api.get).mockResolvedValueOnce({ data: { unread_count: 2 } }).mockResolvedValueOnce({ data: { href: "/trips/uuid" } });
  expect(await getUnreadCount()).toBe(2);
  expect(await getNotificationSource("id")).toBe("/trips/uuid");
  expect(api.get).toHaveBeenLastCalledWith("/notifications/id/source");
});
it("persiste somente categorias e escolhas editáveis", async () => {
  const items = [{ category: "SECURITY" as const, enabled: true, mandatory: true }];
  vi.mocked(api.get).mockResolvedValue({ data: { items } });
  vi.mocked(api.put).mockResolvedValue({ data: { items } });
  expect(await getNotificationPreferences()).toEqual(items);
  expect(await saveNotificationPreferences(items)).toEqual(items);
  expect(api.put).toHaveBeenCalledWith("/notifications/preferences", { items: [{ category: "SECURITY", enabled: true }] });
});
it("preserva falhas da API para a interface tratar", async () => {
  const error = new Error("Falha controlada");
  vi.mocked(api.get).mockRejectedValue(error);
  await expect(listNotifications()).rejects.toBe(error);
});
