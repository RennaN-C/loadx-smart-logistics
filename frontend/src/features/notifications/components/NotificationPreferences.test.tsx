import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { getNotificationPreferences, saveNotificationPreferences, type NotificationPreference } from "../api/notificationsApi";
import { NotificationPreferences } from "./NotificationPreferences";
vi.mock("../api/notificationsApi");
const defaults: NotificationPreference[] = [
  { category: "TRIPS", enabled: true, mandatory: false },
  { category: "OCCURRENCES", enabled: true, mandatory: false },
  { category: "SECURITY", enabled: true, mandatory: true },
];
beforeEach(() => { vi.resetAllMocks(); vi.mocked(getNotificationPreferences).mockResolvedValue(defaults); vi.mocked(saveNotificationPreferences).mockImplementation(async (items) => [...items]); });
function setup() { render(<MemoryRouter><NotificationPreferences /></MemoryRouter>); }
it("consulta preferências reais e mantém segurança obrigatória", async () => {
  setup();
  expect(screen.getByRole("status")).toHaveTextContent("Consultando");
  expect(await screen.findByRole("checkbox", { name: "Segurança" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "Segurança" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Salvar preferências" })).toBeDisabled();
  expect(screen.getByRole("link", { name: /Abrir central/ })).toHaveAttribute("href", "/notifications");
});
it("salva alterações e confirma somente após a API", async () => {
  setup(); fireEvent.click(await screen.findByRole("checkbox", { name: "Viagens" }));
  fireEvent.click(screen.getByRole("button", { name: "Salvar preferências" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Preferências de notificações salvas");
  expect(saveNotificationPreferences).toHaveBeenCalledWith([{ category: "TRIPS", enabled: false, mandatory: false }, ...defaults.slice(1)]);
  expect(screen.getByRole("button", { name: "Salvar preferências" })).toBeDisabled();
});
it("cancelar restaura a consulta sem gravar", async () => {
  setup(); const checkbox = await screen.findByRole("checkbox", { name: "Ocorrências" }); fireEvent.click(checkbox);
  fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(checkbox).toBeChecked(); expect(saveNotificationPreferences).not.toHaveBeenCalled();
});
it("mantém rascunho se salvar falhar e permite nova tentativa", async () => {
  vi.mocked(saveNotificationPreferences).mockRejectedValueOnce(new Error("Indisponível"));
  setup(); const checkbox = await screen.findByRole("checkbox", { name: "Viagens" }); fireEvent.click(checkbox);
  fireEvent.click(screen.getByRole("button", { name: "Salvar preferências" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Suas alterações foram mantidas");
  expect(checkbox).not.toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Salvar preferências" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("salvas"));
});
it("trata falha de consulta sem mostrar preferências inventadas", async () => {
  vi.mocked(getNotificationPreferences).mockRejectedValueOnce(new Error("Indisponível")); setup();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByRole("checkbox", { name: "Viagens" })).toBeChecked();
});
