import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/App";
import { ApiError } from "../../../types/api";
import { getCurrentUser } from "../api/authApi";
import { changeOwnPassword, listOwnSessions, revokeOtherSessions, revokeOwnSession, updateOwnProfile, type OwnSession } from "../api/accountApi";
import type { Role } from "../types";
vi.mock("../api/authApi");
vi.mock("../api/accountApi");
vi.mock("../../dashboard/pages/DashboardPage", () => ({ DashboardPage: () => <h1>Início da operação</h1> }));
const USER = { id: "u1", name: "Conta Fictícia", email: "conta@example.test", role: "ADMIN" as Role, active: true, createdAt: "2026-10-10T00:00:00Z" };
const SESSION: OwnSession = { id: "session-current", current: true, created_at: "2026-10-10T00:00:00Z", last_seen_at: "2026-10-10T00:01:00Z", idle_expires_at: "2026-10-10T00:31:00Z", absolute_expires_at: "2026-10-10T08:00:00Z" };
beforeEach(() => { vi.resetAllMocks(); window.history.replaceState({}, "", "/account"); vi.mocked(getCurrentUser).mockResolvedValue(USER); vi.mocked(listOwnSessions).mockResolvedValue([SESSION, { ...SESSION, id: "session-other", current: false }]); });
async function show() { render(<App />); await screen.findByRole("heading", { name: "Meu perfil", level: 1 }); await screen.findByRole("heading", { name: "Sessão atual" }); }
function fillPassword(confirm = "Nova-senha-ficticia-2026") {
  fireEvent.change(screen.getByLabelText("Senha atual"), { target: { value: "Senha-atual-ficticia" } });
  fireEvent.change(screen.getByLabelText("Nova senha"), { target: { value: "Nova-senha-ficticia-2026" } });
  fireEvent.change(screen.getByLabelText("Confirmar nova senha"), { target: { value: confirm } });
}
describe("OC92 Meu perfil", () => {
  it.each<Role>(["ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER"])("%s acessa sua conta por URL e menu sem novos privilégios", async (role) => {
    vi.mocked(getCurrentUser).mockResolvedValue({ ...USER, role }); await show();
    expect(screen.getByRole("radio", { name: /Automático/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Nome")).toHaveValue(USER.name);
    expect(screen.getByRole("form", { name: "Dados pessoais" })).toHaveTextContent({ ADMIN: "Administrador", LOGISTICS_MANAGER: "Gestor de logística", CHECKER: "Conferente", DRIVER: "Motorista" }[role]);
    expect(screen.queryByLabelText("Perfil de acesso")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Meu perfil" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Voltar ao início" })).toHaveClass("entity-header-link");
    fireEvent.click(screen.getByRole("link", { name: "Voltar ao início" }));
    await screen.findByRole("heading", { name: "Início da operação" });
    fireEvent.click(screen.getByRole("link", { name: "Meu perfil" }));
    await screen.findByRole("heading", { name: "Meu perfil" });
    if (role !== "ADMIN") expect(screen.queryByRole("link", { name: "Configurações" })).not.toBeInTheDocument();
  });
  it("salva dados e atualiza o contexto da conta", async () => {
    vi.mocked(updateOwnProfile).mockResolvedValue({ ...USER, name: "Nome Atualizado" }); await show();
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Nome Atualizado" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar dados pessoais" }));
    await screen.findByText("Dados pessoais salvos com sucesso.");
    expect(updateOwnProfile).toHaveBeenCalledWith("Nome Atualizado", USER.email);
    expect(screen.getAllByText("Nome Atualizado").length).toBeGreaterThan(0);
  });
  it("cancela edição e restaura dados persistidos", async () => {
    await show(); fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Rascunho" } }); fireEvent.click(screen.getByRole("button", { name: "Cancelar" })); expect(screen.getByLabelText("Nome")).toHaveValue(USER.name); expect(updateOwnProfile).not.toHaveBeenCalled();
  });
  it("informa e-mail duplicado sem apresentar resposta privada", async () => {
    vi.mocked(updateOwnProfile).mockRejectedValue(new ApiError("USER_EMAIL_ALREADY_EXISTS", "segredo interno", [], 409)); await show(); fireEvent.click(screen.getByRole("button", { name: "Salvar dados pessoais" })); await screen.findByText(/E-mail já cadastrado/); expect(screen.queryByText("segredo interno")).not.toBeInTheDocument();
  });
  it("não duplica envio enquanto salva", async () => {
    vi.mocked(updateOwnProfile).mockReturnValue(new Promise(() => {})); await show(); const button = screen.getByRole("button", { name: "Salvar dados pessoais" }); fireEvent.click(button); fireEvent.click(button); expect(updateOwnProfile).toHaveBeenCalledOnce(); expect(screen.getByRole("button", { name: "Salvando…" })).toBeDisabled();
  });
  it("valida confirmação e permite mostrar ou ocultar senhas", async () => {
    await show(); fillPassword("diferente"); fireEvent.click(screen.getByRole("button", { name: "Alterar senha" })); await screen.findByText(/confirmação deve ser igual/); expect(changeOwnPassword).not.toHaveBeenCalled(); const input = screen.getByLabelText("Nova senha"); expect(input).toHaveAttribute("type", "password"); fireEvent.click(screen.getByRole("button", { name: "Mostrar senhas" })); expect(input).toHaveAttribute("type", "text"); expect(screen.getByRole("button", { name: "Ocultar senhas" })).toHaveAttribute("aria-pressed", "true");
  });
  it("valida tamanho da senha antes de enviar", async () => {
    await show(); fillPassword("curta"); fireEvent.change(screen.getByLabelText("Nova senha"), { target: { value: "curta" } }); fireEvent.click(screen.getByRole("button", { name: "Alterar senha" })); await screen.findByText(/nova senha deve ter/); expect(changeOwnPassword).not.toHaveBeenCalled();
  });
  it.each(["AUTH_CURRENT_PASSWORD_INVALID", "AUTH_RATE_LIMITED", "VALIDATION_ERROR", "NETWORK_ERROR"])("trata falha de senha %s", async (code) => {
    vi.mocked(changeOwnPassword).mockRejectedValue(new ApiError(code, "resposta privada")); await show(); fillPassword(); fireEvent.click(screen.getByRole("button", { name: "Alterar senha" })); await screen.findByRole("alert"); expect(screen.queryByText("resposta privada")).not.toBeInTheDocument(); expect(screen.getByRole("heading", { name: "Meu perfil" })).toBeInTheDocument();
  });
  it("troca senha e exige novo login com confirmação real", async () => {
    vi.mocked(changeOwnPassword).mockResolvedValue(); await show(); fillPassword(); fireEvent.click(screen.getByRole("button", { name: "Alterar senha" })); await screen.findByText(/Senha alterada. Todas as sessões/); expect(window.location.pathname).toBe("/login"); expect(changeOwnPassword).toHaveBeenCalledWith("Senha-atual-ficticia", "Nova-senha-ficticia-2026");
  });
  it("revoga outras sessões apenas após confirmação e atualiza lista", async () => {
    vi.mocked(revokeOtherSessions).mockResolvedValue(); await show(); fireEvent.click(screen.getByRole("button", { name: "Encerrar outras sessões" })); expect(revokeOtherSessions).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole("button", { name: "Cancelar encerramento" })); expect(revokeOtherSessions).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole("button", { name: "Encerrar outras sessões" })); vi.mocked(listOwnSessions).mockResolvedValue([SESSION]); fireEvent.click(screen.getByRole("button", { name: "Confirmar encerramento" })); await screen.findByText("Sessões selecionadas encerradas."); await waitFor(() => expect(screen.queryByRole("heading", { name: "Outra sessão" })).not.toBeInTheDocument()); expect(revokeOtherSessions).toHaveBeenCalledOnce();
  });
  it("revoga sessão individual e preserva a conta", async () => {
    vi.mocked(revokeOwnSession).mockResolvedValue(); await show(); fireEvent.click(screen.getByRole("button", { name: "Encerrar esta sessão" })); fireEvent.click(screen.getByRole("button", { name: "Confirmar encerramento" })); await screen.findByText("Sessões selecionadas encerradas."); expect(revokeOwnSession).toHaveBeenCalledWith("session-other"); expect(screen.getByRole("heading", { name: "Meu perfil" })).toBeInTheDocument();
  });
  it("revogar sessão atual redireciona ao login", async () => {
    vi.mocked(revokeOwnSession).mockResolvedValue(); await show(); fireEvent.click(screen.getByRole("button", { name: "Encerrar sessão atual" })); fireEvent.click(screen.getByRole("button", { name: "Confirmar encerramento" })); await screen.findByText(/Sessão encerrada. Entre novamente/); expect(window.location.pathname).toBe("/login");
  });
  it("falha parcial em sessões preserva os demais formulários e permite repetir", async () => {
    vi.mocked(listOwnSessions).mockRejectedValue(new ApiError("NETWORK_ERROR", "segredo")); render(<App />); await screen.findByRole("alert"); expect(screen.getByLabelText("Nome")).toHaveValue(USER.name); vi.mocked(listOwnSessions).mockResolvedValue([SESSION]); fireEvent.click(screen.getByRole("button", { name: "Atualizar sessões" })); await screen.findByRole("heading", { name: "Sessão atual" }); expect(screen.queryByText("segredo")).not.toBeInTheDocument();
  });
  it("trata vazio real", async () => { vi.mocked(listOwnSessions).mockResolvedValue([]); render(<App />); await screen.findByText("Nenhuma sessão ativa foi encontrada."); expect(revokeOwnSession).not.toHaveBeenCalled(); });
  it("nega visitante não autenticado", async () => { vi.mocked(getCurrentUser).mockRejectedValue(new ApiError("AUTH_INVALID_TOKEN", "Sessão inválida")); render(<App />); await screen.findByRole("heading", { name: "Entrar" }); expect(listOwnSessions).not.toHaveBeenCalled(); });
  it("mostra carregamento durante a consulta", async () => { vi.mocked(listOwnSessions).mockReturnValue(new Promise(() => {})); render(<App />); await screen.findByText("Carregando sessões…"); expect(within(screen.getByRole("region", { name: "Dados pessoais" })).getByLabelText("Nome")).toBeInTheDocument(); });
});
