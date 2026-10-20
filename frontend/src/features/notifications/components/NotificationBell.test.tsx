import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import * as api from "../api/notificationsApi";
import { NotificationProvider } from "./NotificationProvider";
import { NotificationBell } from "./NotificationBell";
vi.mock("../api/notificationsApi");
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getUnreadCount).mockResolvedValue(3);
  vi.mocked(api.listNotifications).mockResolvedValue({ items: [], page: 1, pageSize: 5, total: 0, totalPages: 0, unreadCount: 0 });
});
function setup() { render(<MemoryRouter><NotificationProvider active><NotificationBell /></NotificationProvider><button type="button">Fora do painel</button></MemoryRouter>); }
it("apresenta contador real e consulta recentes somente ao abrir", async () => {
  setup(); const bell = await screen.findByRole("button", { name: "Notificações, 3 não lidas" });
  expect(api.listNotifications).not.toHaveBeenCalled(); fireEvent.click(bell);
  expect(await screen.findByText("Tudo em dia")).toBeInTheDocument();
  expect(api.listNotifications).toHaveBeenCalledWith({ page_size: 5 });
  expect(screen.getByRole("link", { name: /Abrir central de notificações/ })).toHaveAttribute("href", "/notifications");
});
it("foca o painel e restaura o foco ao fechar por Escape", async () => {
  setup(); const bell = await screen.findByRole("button", { name: "Notificações, 3 não lidas" }); fireEvent.click(bell);
  const heading = screen.getByRole("heading", { name: "Notificações" });
  expect(heading).toHaveFocus(); fireEvent.keyDown(heading, { key: "Escape" });
  expect(bell).toHaveFocus(); expect(bell).toHaveAttribute("aria-expanded", "false");
});
it("fecha ao clicar fora e não prende a navegação por teclado", async () => {
  setup(); fireEvent.click(await screen.findByRole("button", { name: "Notificações, 3 não lidas" }));
  fireEvent.mouseDown(screen.getByRole("button", { name: "Fora do painel" }));
  expect(screen.queryByRole("heading", { name: "Notificações" })).not.toBeInTheDocument();
});
it("contador indisponível não é apresentado como zero", async () => {
  vi.mocked(api.getUnreadCount).mockRejectedValue(new Error("Falha")); setup();
  expect(await screen.findByRole("button", { name: "Notificações, contador indisponível" })).toBeInTheDocument();
  expect(screen.queryByText("0")).not.toBeInTheDocument();
});
it("apresenta erro e permite retry no dropdown", async () => {
  vi.mocked(api.listNotifications).mockRejectedValueOnce(new Error("Falha")); setup();
  fireEvent.click(await screen.findByRole("button", { name: "Notificações, 3 não lidas" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await waitFor(() => expect(screen.getByText("Tudo em dia")).toBeInTheDocument());
});
