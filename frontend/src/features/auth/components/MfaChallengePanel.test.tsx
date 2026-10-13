import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MfaChallengePanel } from "./MfaChallengePanel";
import { OwnMfaPanel } from "./OwnMfaPanel";
import * as identity from "../api/identityApi";
import { ApiError } from "../../../types/api";
vi.mock("../api/identityApi");
const updateUser = vi.fn(); const beginMfa = vi.fn();
vi.mock("../hooks/useAuth", () => ({ useAuth: () => ({ updateUser, beginMfa }) }));
const challenge = { challenge_token: "restricted", purpose: "ENROLL" as const, expires_at: "2026-10-13T12:05:00Z" };
const user = { id: "u", name: "Conta", email: "conta@example.test", role: "ADMIN" as const, active: true, createdAt: "2026-10-13" };
describe("verificação multifator", () => {
  beforeEach(() => vi.clearAllMocks());
  it("configura e verifica posse antes de liberar a conta, mostrando códigos uma vez", async () => {
    vi.mocked(identity.setupMfa).mockResolvedValue("otpauth://totp/LoadX?secret=test");
    vi.mocked(identity.verifyMfa).mockResolvedValue({ user, codes: ["recuperacao"] });
    render(<MfaChallengePanel challenge={challenge} />);
    expect(screen.getByRole("button", { name: "Verificar e continuar" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Preparar autenticador" }));
    await screen.findByLabelText("URI de provisionamento");
    fireEvent.change(screen.getByLabelText("Código do autenticador"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verificar e continuar" }));
    await screen.findByText("recuperacao"); expect(updateUser).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("URI de provisionamento")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Guardei os códigos, continuar" }));
    expect(updateUser).toHaveBeenCalledWith(user);
  });
  it("mantém desafio restrito após erro ou expiração e permite voltar", async () => {
    vi.mocked(identity.verifyMfa).mockRejectedValue(new ApiError("AUTH_MFA_INVALID", "Verificação inválida ou expirada."));
    render(<MfaChallengePanel challenge={{ ...challenge, purpose: "LOGIN" }} />);
    fireEvent.change(screen.getByLabelText("Código do autenticador ou de recuperação"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verificar e continuar" }));
    await screen.findByRole("alert"); expect(updateUser).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Voltar ao login" })); expect(beginMfa).toHaveBeenCalledWith(undefined);
  });
  it("gerencia códigos com senha e segundo fator, sem guardar em storage", async () => {
    vi.mocked(identity.getMfaStatus).mockResolvedValue({ enabled: true, required: true });
    vi.mocked(identity.regenerateCodes).mockResolvedValue(["novo-codigo"]);
    const storage = vi.spyOn(Storage.prototype, "setItem");
    render(<OwnMfaPanel />); await screen.findByText("Ativa");
    fireEvent.change(screen.getByLabelText("Senha atual"), { target: { value: "senha-segura-local" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador ou recuperação"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar ação de segurança" }));
    await screen.findByText("novo-codigo"); expect(identity.regenerateCodes).toHaveBeenCalledWith("senha-segura-local", "123456"); expect(storage).not.toHaveBeenCalled(); storage.mockRestore();
    fireEvent.click(screen.getByRole("button", { name: "Guardei os códigos, continuar" })); expect(screen.queryByText("novo-codigo")).not.toBeInTheDocument();
  });
  it("oferece nova tentativa após falha da consulta", async () => {
    vi.mocked(identity.getMfaStatus).mockRejectedValueOnce(new Error()).mockResolvedValue({ enabled: false, required: false });
    render(<OwnMfaPanel />); fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" })); await waitFor(() => expect(screen.getByText("Não configurada")).toBeInTheDocument());
  });
});
