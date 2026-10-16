import { listProfiles } from "../../access-profiles/api/profilesApi";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, type Page } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import type { Role } from "../../auth/types";
import { RequireSettingsAdmin } from "../../settings/components/RequireSettingsAdmin";
import { getDriver, listDrivers } from "../../drivers/api/driversApi";
import { createUser, getUser, listUsers, updateUser, type UserAccount } from "../api/usersApi";
import { UserManagementPanel } from "./UserManagementPanel";
vi.mock("../api/usersApi");
vi.mock("../../access-profiles/api/profilesApi");
vi.mock("../../auth/hooks/useAuth");
vi.mock("../../drivers/api/driversApi");
const ADMIN: UserAccount = { id: "u1", name: "Admin fictício", email: "admin@example.test", role: "ADMIN", active: true, driverId: null, createdAt: "2026-10-16T00:00:00Z" };
const TARGET: UserAccount = { ...ADMIN, id: "u2", name: "Pessoa exemplo", email: "pessoa@example.test", role: "CHECKER" };
const DRIVER = { id: "d1", name: "Motorista exemplo", active: true, licenseCategory: "D", createdAt: ADMIN.createdAt, document: "fictício", phone: "fictício", licenseNumber: "fictício" };
const updateSession = vi.fn();
function page(items = [ADMIN, TARGET], number = 1, totalPages = 1): Page<UserAccount> { return { items, page: number, pageSize: 20, total: items.length, totalPages }; }
function role(profile: Role = "ADMIN") { vi.mocked(useAuth).mockReturnValue({ status: "authenticated", user: { ...ADMIN, role: profile }, login: vi.fn(), logout: vi.fn(), updateUser: updateSession }); }
function show() { return render(<UserManagementPanel />); }
async function edit(account = TARGET) { vi.mocked(getUser).mockResolvedValue(account); show(); fireEvent.click(await screen.findByRole("button", { name: `Editar ${account.name}` })); return screen.findByRole("dialog", { name: "Editar conta" }); }
function passwords(dialog: HTMLElement, value = "Frase de senha ficticia 2026!") { fireEvent.change(within(dialog).getByLabelText(/^(Senha inicial|Nova senha)$/), { target: { value } }); fireEvent.change(within(dialog).getByLabelText("Confirmar senha"), { target: { value } }); }
async function creating() { show(); fireEvent.click(screen.getByRole("button", { name: "Criar usuário" })); const dialog = screen.getByRole("dialog"); fireEvent.change(within(dialog).getByLabelText("Nome"), { target: { value: "Pessoa nova" } }); fireEvent.change(within(dialog).getByLabelText("E-mail"), { target: { value: "nova@example.test" } }); passwords(dialog); return dialog; }
beforeEach(() => { vi.resetAllMocks(); role(); vi.mocked(listUsers).mockResolvedValue(page()); vi.mocked(getUser).mockResolvedValue(TARGET); vi.mocked(createUser).mockResolvedValue({ ...TARGET, id: "u3" }); vi.mocked(updateUser).mockResolvedValue(TARGET); vi.mocked(listDrivers).mockResolvedValue({ ...page([]), items: [DRIVER] }); vi.mocked(getDriver).mockResolvedValue(DRIVER); });
describe("OC86 gestão de usuários", () => {
  it("lista identidade, estado, vínculo e paginação real", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce(page([ADMIN, { ...TARGET, driverId: "d1" }], 1, 2)); show();
    expect(await screen.findByText(TARGET.email)).toBeInTheDocument(); expect(screen.getByText("Motorista vinculado")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próxima" })); await waitFor(() => expect(listUsers).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
    fireEvent.change(screen.getByLabelText("Buscar por nome"), { target: { value: "Pessoa" } });
    await waitFor(() => expect(listUsers).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, search: "Pessoa" })));
    fireEvent.change(screen.getByLabelText("Filtrar perfil"), { target: { value: "DRIVER" } }); fireEvent.change(screen.getByLabelText("Filtrar estado"), { target: { value: "false" } });
    await waitFor(() => expect(listUsers).toHaveBeenLastCalledWith(expect.objectContaining({ role: "DRIVER", active: false })));
  });
  it("cria conta e limpa campos secretos após salvar", async () => {
    const dialog = await creating(); fireEvent.click(within(dialog).getByRole("button", { name: "Salvar usuário" }));
    await screen.findByText("Usuário criado com sucesso."); expect(createUser).toHaveBeenCalledWith({ name: "Pessoa nova", email: "nova@example.test", role: "CHECKER", active: true, driverId: null, customProfileId: null, password: "Frase de senha ficticia 2026!" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); expect(screen.queryByDisplayValue("Frase de senha ficticia 2026!")).not.toBeInTheDocument(); expect(listUsers).toHaveBeenCalledTimes(2);
  });
  it("valida tamanho e confirmação antes de enviar", async () => {
    const dialog = await creating(); passwords(dialog, "curta"); fireEvent.click(within(dialog).getByRole("button", { name: "Salvar usuário" })); expect(await screen.findByRole("alert")).toHaveTextContent("15 a 128");
    passwords(dialog); fireEvent.change(within(dialog).getByLabelText("Confirmar senha"), { target: { value: "diferente" } }); fireEvent.click(within(dialog).getByRole("button", { name: "Salvar usuário" })); expect(screen.getByRole("alert")).toHaveTextContent("confirmação"); expect(createUser).not.toHaveBeenCalled();
  });
  it.each(["USER_EMAIL_ALREADY_EXISTS", "USER_DRIVER_NOT_FOUND", "USER_DRIVER_ALREADY_LINKED", "USER_LAST_ACTIVE_ADMIN_REQUIRED", "VALIDATION_ERROR"])("traduz %s sem revelar resposta privada", async (code) => {
    vi.mocked(createUser).mockRejectedValue(new ApiError(code, "RESPOSTA-PRIVADA")); const dialog = await creating(); fireEvent.click(within(dialog).getByRole("button", { name: "Salvar usuário" })); await screen.findByRole("alert");
    expect(screen.queryByText("RESPOSTA-PRIVADA")).not.toBeInTheDocument(); expect(within(dialog).getByLabelText("Senha inicial")).toHaveValue(""); expect(within(dialog).getByLabelText("Nome")).toHaveValue("Pessoa nova");
  });
  it("confirma perfil antes de enviar somente os campos alterados", async () => {
    const dialog = await edit(); fireEvent.change(within(dialog).getByLabelText("Perfil de acesso"), { target: { value: "LOGISTICS_MANAGER" } }); fireEvent.click(within(dialog).getByRole("button", { name: "Salvar usuário" }));
    expect(screen.getByRole("button", { name: "Confirmar alterações" })).toHaveFocus(); expect(updateUser).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Voltar ao formulário" })); expect(screen.getByLabelText("Perfil de acesso")).toHaveValue("LOGISTICS_MANAGER"); expect(screen.getByLabelText("Nome")).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Salvar usuário" })); fireEvent.click(screen.getByRole("button", { name: "Confirmar alterações" })); await screen.findByText("Usuário atualizado com sucesso.");
    expect(updateUser).toHaveBeenCalledWith(TARGET.id, { role: "LOGISTICS_MANAGER" });
  });
  it.each([true, false])("altera estado para %s após confirmação", async (active) => {
    const account = { ...TARGET, active: !active }; vi.mocked(listUsers).mockResolvedValue(page([ADMIN, account])); const dialog = await edit(account);
    fireEvent.change(within(dialog).getByLabelText("Estado da conta"), { target: { value: String(active) } }); fireEvent.click(screen.getByRole("button", { name: "Salvar usuário" })); expect(updateUser).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole("button", { name: "Confirmar alterações" })); await screen.findByText("Usuário atualizado com sucesso."); expect(updateUser).toHaveBeenCalledWith(TARGET.id, { active });
  });
  it("respeita bloqueio do último ADMIN sem alterar sessão local", async () => {
    vi.mocked(updateUser).mockRejectedValue(new ApiError("USER_LAST_ACTIVE_ADMIN_REQUIRED", "privado")); const dialog = await edit(ADMIN);
    fireEvent.change(within(dialog).getByLabelText("Estado da conta"), { target: { value: "false" } }); fireEvent.click(screen.getByRole("button", { name: "Salvar usuário" })); expect(screen.getByText(/Esta é sua conta/)).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "Confirmar alterações" })); await screen.findByRole("alert"); expect(updateSession).not.toHaveBeenCalled(); expect(screen.getByLabelText("Estado da conta")).toHaveValue("false");
  });
  it("vincula e desvincula motorista com confirmação", async () => {
    const dialog = await edit(); fireEvent.change(within(dialog).getByLabelText("Perfil de acesso"), { target: { value: "DRIVER" } }); await screen.findByRole("option", { name: DRIVER.name });
    fireEvent.change(screen.getByLabelText("Motorista vinculado"), { target: { value: DRIVER.id } }); fireEvent.click(screen.getByRole("button", { name: "Salvar usuário" })); fireEvent.click(screen.getByRole("button", { name: "Confirmar alterações" })); await screen.findByText("Usuário atualizado com sucesso."); expect(updateUser).toHaveBeenCalledWith(TARGET.id, { role: "DRIVER", driverId: DRIVER.id });
  });
  it("remove vínculo ao trocar DRIVER por outro perfil", async () => {
    const account = { ...TARGET, role: "DRIVER" as Role, driverId: DRIVER.id }; vi.mocked(listUsers).mockResolvedValue(page([ADMIN, account])); const dialog = await edit(account);
    fireEvent.change(within(dialog).getByLabelText("Perfil de acesso"), { target: { value: "CHECKER" } }); fireEvent.click(screen.getByRole("button", { name: "Salvar usuário" })); fireEvent.click(screen.getByRole("button", { name: "Confirmar alterações" })); await screen.findByText("Usuário atualizado com sucesso."); expect(updateUser).toHaveBeenCalledWith(TARGET.id, { role: "CHECKER", driverId: null });
  });
  it("atualiza a identidade da própria conta sem armazenar vínculo no contexto", async () => {
    vi.mocked(updateUser).mockResolvedValue({ ...ADMIN, name: "Novo nome" }); const dialog = await edit(ADMIN); fireEvent.change(within(dialog).getByLabelText("Nome"), { target: { value: "Novo nome" } }); fireEvent.click(screen.getByRole("button", { name: "Salvar usuário" })); await screen.findByText("Usuário atualizado com sucesso."); expect(updateSession).toHaveBeenCalledWith(expect.objectContaining({ name: "Novo nome" })); expect(updateSession.mock.calls[0][0]).not.toHaveProperty("driverId");
  });
  it("encerra contexto após redefinir a própria senha", async () => {
    vi.mocked(updateUser).mockResolvedValue(ADMIN); const dialog = await edit(ADMIN); fireEvent.click(within(dialog).getByLabelText("Redefinir senha administrativamente")); passwords(dialog); fireEvent.click(screen.getByRole("button", { name: "Salvar usuário" })); expect(screen.queryByDisplayValue("Frase de senha ficticia 2026!")).not.toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "Confirmar alterações" })); await waitFor(() => expect(updateSession).toHaveBeenCalledWith(null, "session-revoked")); expect(listUsers).toHaveBeenCalledTimes(1);
  });
  it("bloqueia abertura de outra operação enquanto busca o detalhe", async () => {
    vi.mocked(getUser).mockReturnValue(new Promise(() => {})); show();
    fireEvent.click(await screen.findByRole("button", { name: `Editar ${TARGET.name}` }));
    expect(screen.getByRole("button", { name: "Criar usuário" })).toBeDisabled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("não duplica submissão nem fecha enquanto salva", async () => {
    vi.mocked(createUser).mockReturnValue(new Promise(() => {})); const dialog = await creating(); fireEvent.click(within(dialog).getByRole("button", { name: "Salvar usuário" })); fireEvent.submit(screen.getByRole("form", { name: "Criar usuário" })); fireEvent.keyDown(document, { key: "Escape" }); expect(createUser).toHaveBeenCalledOnce(); expect(screen.getByRole("dialog")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Salvando…" })).toBeDisabled();
  });
  it("distingue loading, erro/retry e vazio", async () => {
    vi.mocked(listUsers).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "privado")).mockResolvedValueOnce(page([])); show(); expect(screen.getByText("Carregando usuários…")).toBeInTheDocument(); await screen.findByRole("alert"); fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" })); await screen.findByText("Nenhum usuário encontrado com estes filtros.");
  });
  it.each<Role>(["LOGISTICS_MANAGER", "CHECKER", "DRIVER"])("%s não acessa URL administrativa nem consulta usuários", async (profile) => {
    role(profile); render(<MemoryRouter initialEntries={["/settings#settings-users"]}><Routes><Route element={<RequireSettingsAdmin />}><Route path="settings" element={<UserManagementPanel />} /></Route></Routes></MemoryRouter>); expect(await screen.findByRole("heading", { name: "Acesso negado" })).toBeInTheDocument(); expect(listUsers).not.toHaveBeenCalled();
  });
});


describe("OC112 associação de perfil personalizado", () => {
  it("seleciona perfil real e envia a associação no contrato existente", async () => {
    vi.resetAllMocks(); role();
    vi.mocked(listUsers).mockResolvedValue(page([ADMIN]));
    vi.mocked(listProfiles).mockResolvedValue({ items: [{ id: "p1", name: "Consulta de frota", description: "", active: true, version: 1, permissions: ["loadx.trucks.read"], user_count: 0, system_role: null }], page: 1, pageSize: 20, total: 1, totalPages: 1 });
    vi.mocked(createUser).mockResolvedValue({ ...TARGET, role: "CUSTOM", customProfileId: "p1" });
    const dialog = await creating();
    fireEvent.change(within(dialog).getByLabelText("Perfil de acesso"), { target: { value: "CUSTOM" } });
    fireEvent.change(await within(dialog).findByLabelText("Permissões de acesso"), { target: { value: "p1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Salvar usuário" }));
    await screen.findByText("Usuário criado com sucesso.");
    expect(createUser).toHaveBeenCalledWith(expect.objectContaining({ role: "CUSTOM", customProfileId: "p1", driverId: null }));
  });
});
