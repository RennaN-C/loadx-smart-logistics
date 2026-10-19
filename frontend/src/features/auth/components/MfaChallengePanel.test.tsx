import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MfaChallengePanel } from "./MfaChallengePanel";
import { OwnMfaPanel } from "./OwnMfaPanel";
import * as identity from "../api/identityApi";
import { ApiError } from "../../../types/api";
vi.mock("../api/identityApi");
const updateUser = vi.fn(); const beginMfa = vi.fn();
vi.mock("../hooks/useAuth", () => ({ useAuth: () => ({ updateUser, beginMfa }) }));
const challenge = { challenge_token: "restricted", purpose: "ENROLL" as const, expires_at: "2099-10-13T12:05:00Z" };
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
  it("preserva a chave em rerender e remove segredos ao expirar", async () => {
    vi.mocked(identity.setupMfa).mockResolvedValue("otpauth://totp/LoadX?secret=JBSWY3DPEHPK3PXP");
    const { rerender } = render(<MfaChallengePanel challenge={challenge} />);
    fireEvent.click(screen.getByRole("button", { name: "Preparar autenticador" }));
    await screen.findByTitle("QR Code para configurar o autenticador LoadX");
    rerender(<MfaChallengePanel challenge={challenge} />);
    expect(identity.setupMfa).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Gerar outra chave" })).not.toBeInTheDocument();
    rerender(<MfaChallengePanel challenge={{ ...challenge, expires_at: "2000-01-01T00:00:00Z" }} />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Esta etapa expirou"), { timeout: 2000 });
    expect(screen.queryByTitle("QR Code para configurar o autenticador LoadX")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verificar e continuar" })).toBeDisabled();
  });
  it("permite tentar preparar após falha", async () => {
    vi.mocked(identity.setupMfa).mockRejectedValueOnce(new Error());
    render(<MfaChallengePanel challenge={challenge} />);
    fireEvent.click(screen.getByRole("button", { name: "Preparar autenticador" }));
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: "Preparar autenticador" })).toBeEnabled();
  });
  it.each([false, true])("envia opt-in explícito %s somente em LOGIN", async checked => {
    vi.mocked(identity.verifyMfa).mockResolvedValue({ user, codes: [] });
    render(<MfaChallengePanel challenge={{ ...challenge, purpose: "LOGIN", trusted_device_days: 30 }} />);
    const checkbox = screen.getByRole("checkbox", { name: "Confiar neste dispositivo por 30 dias" });
    expect(checkbox).not.toBeChecked();
    expect(checkbox).toHaveAccessibleDescription(/Apenas o código do autenticador cria confiança/);
    if (checked) fireEvent.click(checkbox);
    fireEvent.change(screen.getByLabelText("Código do autenticador ou de recuperação"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verificar e continuar" }));
    await waitFor(() => expect(identity.verifyMfa).toHaveBeenCalledWith(challenge.challenge_token, "123456", checked));
  });
  it.each(["ENROLL", "LOGIN"] as const)("não oferece confiança quando inelegível em %s", purpose => {
    render(<MfaChallengePanel challenge={{ ...challenge, purpose, trusted_device_days: purpose === "ENROLL" ? 30 : null }} />);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });
  it("gerencia códigos com senha e segundo fator, sem guardar em storage", async () => {
    vi.mocked(identity.getMfaStatus).mockResolvedValue({ enabled: true, required: true });
    vi.mocked(identity.regenerateCodes).mockResolvedValue(["novo-codigo"]);
    const storage = vi.spyOn(Storage.prototype, "setItem");
    render(<OwnMfaPanel />); await screen.findByText("Ativa");
    fireEvent.change(screen.getByLabelText("Senha atual para gerenciar MFA"), { target: { value: "senha-segura-local" } });
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
