import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import * as api from "../api/notificationsApi";
import { NotificationProvider } from "../components/NotificationProvider";
import { NotificationBell } from "../components/NotificationBell";
import { NotificationsPage } from "./NotificationsPage";
vi.mock("../api/notificationsApi");
const original: api.NotificationItem[] = [
  { id: "one", event_type: "TRIP_STARTED", category: "TRIPS", title: "Viagem iniciada", summary: "Atualização na viagem 12345678.", created_at: "2026-10-20T12:00:00Z", received_at: "2026-10-20T12:00:00Z", read_at: null },
  { id: "two", event_type: "OCCURRENCE_REGISTERED", category: "OCCURRENCES", title: "Nova ocorrência", summary: "Atualização na viagem 12345678.", created_at: "2026-10-20T11:00:00Z", received_at: "2026-10-20T11:00:00Z", read_at: null },
];
let items: api.NotificationItem[];
beforeEach(() => {
  vi.resetAllMocks(); items = structuredClone(original);
  vi.mocked(api.getUnreadCount).mockResolvedValue(2);
  vi.mocked(api.listNotifications).mockImplementation(async (filters = {}) => {
    const filtered = items.filter((item) => (!filters.category || item.category === filters.category) && (filters.read === undefined || Boolean(item.read_at) === filters.read));
    return { items: filtered, page: filters.page ?? 1, pageSize: 20, total: filtered.length, totalPages: 1, unreadCount: items.filter((item) => !item.read_at).length };
  });
  vi.mocked(api.markNotificationRead).mockImplementation(async (id) => { const item = items.find((item) => item.id === id)!; item.read_at = "2026-10-20T13:00:00Z"; return item; });
  vi.mocked(api.markAllNotificationsRead).mockImplementation(async () => { items = items.map((item) => ({ ...item, read_at: "2026-10-20T13:00:00Z" })); return 2; });
  vi.mocked(api.getNotificationSource).mockResolvedValue("/trips/existing");
});
function setup(path = "/notifications", bell = false) {
  render(<MemoryRouter initialEntries={[path]}><NotificationProvider active>{bell && <NotificationBell />}<Routes><Route path="/notifications" element={<NotificationsPage />} /><Route path="/trips/existing" element={<h1>Viagem existente</h1>} /></Routes></NotificationProvider></MemoryRouter>);
}
it("consulta caixa persistida e mostra acesso às preferências", async () => {
  setup(); expect(await screen.findByText("Viagem iniciada")).toBeInTheDocument();
  expect(screen.getByText("Nova ocorrência")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Preferências/ })).toHaveAttribute("href", "/account#notification-preferences");
  expect(api.listNotifications).toHaveBeenCalledWith({ page: 1, page_size: 20, sort_order: "desc", category: undefined, read: undefined });
});
it("restaura filtros da URL e consulta o backend ao alterar", async () => {
  setup("/notifications?category=OCCURRENCES&read=false&sort_order=asc&page=2");
  expect(await screen.findByText("Nova ocorrência")).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "Categoria" })).toHaveValue("OCCURRENCES");
  expect(api.listNotifications).toHaveBeenCalledWith({ page: 2, page_size: 20, sort_order: "asc", category: "OCCURRENCES", read: false });
  fireEvent.change(screen.getByRole("combobox", { name: "Categoria" }), { target: { value: "TRIPS" } });
  expect(await screen.findByText("Viagem iniciada")).toBeInTheDocument();
  expect(api.listNotifications).toHaveBeenLastCalledWith({ page: 1, page_size: 20, sort_order: "asc", category: "TRIPS", read: false });
});
it("sincroniza leitura individual e contador do sino", async () => {
  setup("/notifications", true); await screen.findByText("Viagem iniciada");
  fireEvent.click(screen.getByRole("button", { name: "Marcar como lida: Viagem iniciada" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Notificações, 1 não lidas" })).toBeInTheDocument());
  expect(api.markNotificationRead).toHaveBeenCalledWith("one");
  expect(screen.getByRole("status")).toHaveTextContent("Notificação marcada");
});
it("marca todas sem modificar outras caixas ou inventar sucesso", async () => {
  setup(); await screen.findByText("Viagem iniciada");
  fireEvent.click(screen.getByRole("button", { name: "Marcar todas como lidas" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Marcar todas como lidas" })).toBeDisabled());
  expect(api.markAllNotificationsRead).toHaveBeenCalledOnce();
});
it("abre somente a origem retornada e autorizada pelo backend", async () => {
  setup(); fireEvent.click(await screen.findByRole("button", { name: "Abrir operação: Viagem iniciada" }));
  expect(await screen.findByRole("heading", { name: "Viagem existente" })).toBeInTheDocument();
  expect(api.getNotificationSource).toHaveBeenCalledWith("one");
});
it("não navega ou marca leitura quando a origem está proibida", async () => {
  vi.mocked(api.getNotificationSource).mockRejectedValue(new Error("Acesso revogado")); setup();
  fireEvent.click(await screen.findByRole("button", { name: "Abrir operação: Viagem iniciada" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Seu acesso pode ter mudado");
  expect(api.markNotificationRead).not.toHaveBeenCalled();
  expect(screen.queryByRole("heading", { name: "Viagem existente" })).not.toBeInTheDocument();
});
it("trata falha de leitura sem anunciar sucesso", async () => {
  vi.mocked(api.markNotificationRead).mockRejectedValue(new Error("Falha")); setup();
  fireEvent.click(await screen.findByRole("button", { name: "Marcar como lida: Viagem iniciada" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByText("Notificação marcada como lida.")).not.toBeInTheDocument();
});
it("oferece retry em falha de consulta", async () => {
  vi.mocked(api.listNotifications).mockRejectedValueOnce(new Error("Falha")); setup();
  expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível carregar");
  expect(screen.queryByText("Nenhuma notificação por aqui")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Viagem iniciada")).toBeInTheDocument();
});
it("mostra vazio real e não permite marcar todas", async () => {
  items = []; setup();
  expect(await screen.findByText("Nenhuma notificação por aqui")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Marcar todas como lidas" })).toBeDisabled();
});
it("permite acessar outras páginas pela paginação real", async () => {
  vi.mocked(api.listNotifications).mockResolvedValue({ items: original, page: 1, pageSize: 20, total: 21, totalPages: 2, unreadCount: 2 });
  setup(); fireEvent.click(await screen.findByRole("button", { name: "Próxima" }));
  await waitFor(() => expect(api.listNotifications).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
});
