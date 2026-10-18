import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "../../auth/hooks/useAuth";
import { listProfiles, permissionCatalog } from "../../access-profiles/api/profilesApi";
import { listUsers } from "../api/usersApi";
import { makePage } from "../../../tests/makePage";
import { AccessManagementPanel } from "./AccessManagementPanel";

vi.mock("../../auth/hooks/useAuth");
vi.mock("../../access-profiles/api/profilesApi");
vi.mock("../api/usersApi");
const ADMIN = { id: "a", name: "Admin fictício", email: "admin@example.test", active: true, role: "ADMIN" as const, createdAt: "2026-10-18T00:00:00Z" };
function Location() { const navigate = useNavigate(); return <><output aria-label="Endereço atual">{useLocation().hash}</output><button type="button" onClick={() => navigate(-1)}>Anterior do navegador</button><button type="button" onClick={() => navigate(1)}>Próxima do navegador</button></>; }
function show(hash = "#settings-users") { return render(<MemoryRouter initialEntries={[`/settings${hash}`]}><AccessManagementPanel /><Location /></MemoryRouter>); }
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(useAuth).mockReturnValue({ status: "authenticated", user: ADMIN, login: vi.fn(), logout: vi.fn(), updateUser: vi.fn() });
  vi.mocked(listUsers).mockResolvedValue(makePage([]));
  vi.mocked(listProfiles).mockResolvedValue(makePage([]));
  vi.mocked(permissionCatalog).mockResolvedValue([]);
});
describe("gestão unificada da OC112", () => {
  it("abre o link antigo na aba de perfis sem manter página duplicada", async () => {
    show("#settings-profiles");
    expect(await screen.findByLabelText("Endereço atual")).toHaveTextContent("#settings-users-profiles");
    expect(screen.getByRole("tab", { name: "Perfis de acesso" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("button", { name: "Criar usuário" })).not.toBeInTheDocument();
    expect(listUsers).not.toHaveBeenCalled();
  });
  it("permite alternar abas com setas, Home e End mantendo foco", async () => {
    show();
    const users = screen.getByRole("tab", { name: "Usuários" });
    users.focus(); fireEvent.keyDown(users, { key: "ArrowRight" });
    const profiles = screen.getByRole("tab", { name: "Perfis de acesso" });
    expect(profiles).toHaveFocus();
    expect(profiles).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(profiles, { key: "Home" });
    expect(users).toHaveFocus();
    fireEvent.keyDown(users, { key: "End" });
    expect(profiles).toHaveFocus();
    await screen.findByText("Nenhum perfil nesta página.");
  });
  it("restaura a aba pelo histórico anterior e próximo", async () => {
    show();
    fireEvent.click(screen.getByRole("tab", { name: "Perfis de acesso" }));
    fireEvent.click(screen.getByRole("button", { name: "Anterior do navegador" }));
    expect(await screen.findByRole("tab", { name: "Usuários", selected: true })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próxima do navegador" }));
    expect(await screen.findByRole("tab", { name: "Perfis de acesso", selected: true })).toBeInTheDocument();
    await screen.findByText("Nenhum perfil nesta página.");
  });
  it("leva do formulário aos perfis e preserva dados da conta ao voltar, limpando senha", async () => {
    show();
    fireEvent.click(screen.getByRole("button", { name: "Criar usuário" }));
    const form = screen.getByRole("form", { name: "Criar usuário" });
    fireEvent.change(within(form).getByLabelText("Nome"), { target: { value: "Rascunho da pessoa" } });
    fireEvent.change(within(form).getByLabelText("Senha inicial"), { target: { value: "Senha ficticia de teste!" } });
    fireEvent.click(within(form).getByRole("button", { name: "Gerenciar perfis de acesso →" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Perfis de acesso" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Perfis de acesso" })).toHaveFocus();
    fireEvent.click(screen.getByRole("tab", { name: "Usuários" }));
    expect(screen.getByLabelText("Nome")).toHaveValue("Rascunho da pessoa");
    expect(screen.getByLabelText("Senha inicial")).toHaveValue("");
    expect(screen.getByLabelText("Nome")).toHaveFocus();
    await screen.findByRole("alert"); // resumo indisponível com coleção vazia, sem dados fictícios
  });
});
