import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCurrentUser, login, logout } from "../features/auth/api/authApi";
import type { AuthenticatedUser, Role } from "../features/auth/types";
import { notifyIfSessionInvalidated } from "../services/api";
import { ApiError } from "../types/api";
import { App } from "./App";

vi.mock("../features/auth/api/authApi");
vi.mock("../features/settings/api/companyProfileApi", () => ({ getCompanyProfile: vi.fn(async () => null) }));
vi.mock("../features/dashboard/pages/DashboardPage", () => ({ DashboardPage: () => <h1>Início da operação</h1> }));

const USER: AuthenticatedUser = {
  id: "00000000-0000-0000-0000-000000000085", name: "Conta de teste",
  email: "admin@example.test", role: "ADMIN", active: true, createdAt: "2026-10-09T00:00:00Z",
};
const OTHER_ROLES: Role[] = ["LOGISTICS_MANAGER", "CHECKER", "DRIVER"];

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState({}, "", "/settings");
  vi.mocked(getCurrentUser).mockResolvedValue(USER);
  vi.mocked(logout).mockResolvedValue(undefined);
});

function account() { return screen.getByRole("region", { name: "Conta e administração" }); }

describe("OC85: navegação e autorização na aplicação", () => {
  it("ADMIN acessa a rota real e consulta o contexto da sessão sem buscar outra identidade", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Configurações", level: 1 });
    const menu = screen.getByRole("navigation", { name: "Navegação principal" });
    expect(within(menu).getByRole("link", { name: "Configurações" })).toHaveAttribute("aria-current", "page");
    expect(within(account()).getByText(USER.name)).toBeInTheDocument();
    expect(within(account()).getByText(USER.email)).toBeInTheDocument();
    expect(within(account()).getByText("Administrador")).toBeInTheDocument();
    expect(getCurrentUser).toHaveBeenCalledOnce();
    expect(login).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /salvar|criar/i })).not.toBeInTheDocument();
  });

  it.each(OTHER_ROLES)("%s não vê Configurações e recebe acesso negado ao usar endereço direto", async (role) => {
    vi.mocked(getCurrentUser).mockResolvedValue({ ...USER, role });
    render(<App />);
    await screen.findByRole("heading", { name: "Acesso negado" });
    expect(screen.getByRole("alert")).toHaveTextContent("somente para administradores ativos");
    expect(screen.queryByRole("link", { name: "Configurações" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Conta e administração" })).not.toBeInTheDocument();
    expect(screen.queryByText("Administração", { exact: true })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Voltar ao início" }));
    await screen.findByRole("heading", { name: "Início da operação" });
  });

  it("ADMIN chega pelo menu e marca somente Configurações como tela ativa", async () => {
    window.history.replaceState({}, "", "/");
    render(<App />);
    await screen.findByRole("heading", { name: "Início da operação" });
    fireEvent.click(screen.getByRole("link", { name: "Configurações" }));
    await screen.findByRole("heading", { name: "Configurações", level: 1 });
    expect(window.location.pathname).toBe("/settings");
    expect(screen.getByRole("link", { name: "Início" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Configurações" })).toHaveAttribute("aria-current", "page");
  });

  it("aguarda restauração da sessão sem exibir menu ou dados administrativos", async () => {
    let restore!: (user: AuthenticatedUser) => void;
    vi.mocked(getCurrentUser).mockReturnValue(new Promise((resolve) => { restore = resolve; }));
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando");
    expect(screen.queryByText(USER.email)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Configurações" })).not.toBeInTheDocument();
    await act(async () => restore(USER));
    expect(screen.getByRole("heading", { name: "Configurações", level: 1 })).toBeInTheDocument();
  });

  it.each([
    new ApiError("AUTH_INVALID_TOKEN", "Sessão expirada", [], 401),
    new ApiError("AUTH_FORBIDDEN", "Acesso negado", [], 403),
    new ApiError("NETWORK_ERROR", "Sem conexão"),
  ])("falha de restauração (%s) segue login sem montar configurações", async (error) => {
    vi.mocked(getCurrentUser).mockRejectedValue(error);
    render(<App />);
    await screen.findByRole("button", { name: "Entrar" });
    expect(window.location.pathname).toBe("/login");
    expect(screen.queryByRole("region", { name: "Conta e administração" })).not.toBeInTheDocument();
    expect(window.history.state.usr.from.pathname).toBe("/settings");
  });

  it("administrador inativo não recebe conteúdo protegido", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({ ...USER, active: false });
    render(<App />);
    await screen.findByRole("heading", { name: "Acesso negado" });
    expect(screen.queryByText(USER.email)).not.toBeInTheDocument();
  });

  it("invalidação da sessão remove dados e redireciona para login", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Configurações", level: 1 });
    act(() => notifyIfSessionInvalidated(new ApiError("AUTH_INVALID_TOKEN", "Sessão expirada", [], 401)));
    await screen.findByRole("button", { name: "Entrar" });
    expect(screen.queryByText(USER.email)).not.toBeInTheDocument();
    expect(window.location.pathname).toBe("/login");
  });

  it("sair das configurações reutiliza logout revogável e remove a página", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Configurações", level: 1 });
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    await screen.findByRole("button", { name: "Entrar" });
    expect(logout).toHaveBeenCalledOnce();
    expect(screen.queryByText(USER.email)).not.toBeInTheDocument();
  });

  it("separa regiões acessíveis e não oferece links para OCs futuras", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Configurações", level: 1 });
    expect(screen.getByRole("region", { name: "Configurações do LoadX" })).toBeInTheDocument();
    for (const label of ["Gestão de usuários", "Segurança da conta"]) {
      expect(within(account()).getByRole("heading", { name: label, level: 3 })).toBeInTheDocument();
      expect(screen.queryByRole("link", { name: label })).not.toBeInTheDocument();
    }
    expect(screen.getByRole("region", { name: "Dados da empresa" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dados da empresa" })).toHaveAttribute("href", "#settings-company");
    const sections = screen.getByRole("navigation", { name: "Seções de configurações" });
    for (const link of within(sections).getAllByRole("link")) {
      const id = link.getAttribute("href")!.slice(1);
      expect(document.getElementById(id)).not.toBeNull();
    }
    await waitFor(() => expect(getCurrentUser).toHaveBeenCalledOnce());
  });
});
