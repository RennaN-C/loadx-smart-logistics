import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, it, expect, beforeEach } from "vitest";
import { PasswordRecoveryPage } from "./PasswordRecoveryPage";
import * as identity from "../api/identityApi";
import { ApiError } from "../../../types/api";
vi.mock("../api/identityApi");
beforeEach(() => { vi.clearAllMocks(); globalThis.history.replaceState(null, "", "/password-recovery"); });
it("solicita recuperação e mostra resposta neutra", async () => {
  vi.mocked(identity.requestRecovery).mockResolvedValue(); render(<MemoryRouter><PasswordRecoveryPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "conta@example.test" } }); fireEvent.click(screen.getByRole("button", { name: "Solicitar recuperação" }));
  expect(await screen.findByText(/Se a conta for elegível/)).toBeInTheDocument(); expect(identity.requestRecovery).toHaveBeenCalledWith("conta@example.test"); expect(screen.getByRole("link", { name: "Voltar ao login" })).toHaveAttribute("href", "/login");
});
it("remove token do endereço, valida confirmação e não autentica após reset", async () => {
  globalThis.history.replaceState(null, "", "/password-reset#token=one-time"); vi.mocked(identity.confirmRecovery).mockResolvedValue(); render(<MemoryRouter><PasswordRecoveryPage reset /></MemoryRouter>);
  expect(globalThis.location.hash).toBe(""); fireEvent.change(screen.getByLabelText("Nova senha"), { target: { value: "frase-segura-nova" } }); fireEvent.change(screen.getByLabelText("Confirmar nova senha"), { target: { value: "outra-frase-diferente" } }); fireEvent.click(screen.getByRole("button", { name: "Redefinir senha" })); expect(await screen.findByRole("alert")).toHaveTextContent("As senhas devem ser iguais"); expect(identity.confirmRecovery).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Confirmar nova senha"), { target: { value: "frase-segura-nova" } }); fireEvent.click(screen.getByRole("button", { name: "Redefinir senha" })); expect(await screen.findByText(/Senha redefinida/)).toBeInTheDocument(); expect(identity.confirmRecovery).toHaveBeenCalledWith("one-time", "frase-segura-nova");
});
it("trata indisponibilidade sem afirmar entrega", async () => {
  vi.mocked(identity.requestRecovery).mockRejectedValue(new ApiError("AUTH_IDENTITY_UNAVAILABLE", "Serviço indisponível.")); render(<MemoryRouter><PasswordRecoveryPage /></MemoryRouter>); fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "conta@example.test" } }); fireEvent.click(screen.getByRole("button", { name: "Solicitar recuperação" })); expect(await screen.findByRole("alert")).toHaveTextContent("Serviço indisponível"); expect(screen.queryByText(/você receberá/)).not.toBeInTheDocument();
});
it("não envia reset sem token", () => { render(<MemoryRouter><PasswordRecoveryPage reset /></MemoryRouter>); expect(screen.getByRole("button", { name: "Redefinir senha" })).toBeDisabled(); });
