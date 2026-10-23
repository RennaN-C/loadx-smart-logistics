import { StrictMode } from "react";
import { act, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, it, expect, beforeEach } from "vitest";
import { PasswordRecoveryPage } from "./PasswordRecoveryPage";
import * as identity from "../api/identityApi";
import { ApiError } from "../../../types/api";
vi.mock("../api/identityApi");
const updateUser = vi.fn();
vi.mock("../hooks/useAuth", () => ({ useAuth: () => ({ updateUser }) }));
beforeEach(() => { vi.clearAllMocks(); globalThis.history.replaceState(null, "", "/password-recovery"); });
it("solicita recuperação e mostra resposta neutra", async () => {
  vi.mocked(identity.requestRecovery).mockResolvedValue(); render(<MemoryRouter><PasswordRecoveryPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "conta@example.test" } }); fireEvent.click(screen.getByRole("button", { name: "Solicitar recuperação" }));
  expect(await screen.findByText(/Se a conta for elegível/)).toBeInTheDocument(); expect(identity.requestRecovery).toHaveBeenCalledWith("conta@example.test"); expect(screen.getByRole("link", { name: "Voltar ao login" })).toHaveAttribute("href", "/login");
});
it("remove token do endereço, valida confirmação e não autentica após reset", async () => {
  globalThis.history.replaceState(null, "", "/password-reset#token=one-time"); vi.mocked(identity.confirmRecovery).mockResolvedValue(); render(<MemoryRouter><PasswordRecoveryPage reset /></MemoryRouter>);
  expect(globalThis.location.hash).toBe(""); fireEvent.change(screen.getByLabelText("Nova senha"), { target: { value: "frase-segura-nova" } }); fireEvent.change(screen.getByLabelText("Confirmar nova senha"), { target: { value: "outra-frase-diferente" } }); fireEvent.click(screen.getByRole("button", { name: "Redefinir senha" })); expect(await screen.findByRole("alert")).toHaveTextContent("As senhas devem ser iguais"); expect(identity.confirmRecovery).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Confirmar nova senha"), { target: { value: "frase-segura-nova" } }); fireEvent.click(screen.getByRole("button", { name: "Redefinir senha" })); expect(await screen.findByText(/Senha redefinida/)).toBeInTheDocument(); expect(identity.confirmRecovery).toHaveBeenCalledWith("one-time", "frase-segura-nova"); expect(updateUser).toHaveBeenCalledWith(null, "password-changed");
});
it("trata indisponibilidade sem afirmar entrega", async () => {
  vi.mocked(identity.requestRecovery).mockRejectedValue(new ApiError("AUTH_IDENTITY_UNAVAILABLE", "Serviço indisponível.")); render(<MemoryRouter><PasswordRecoveryPage /></MemoryRouter>); fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "conta@example.test" } }); fireEvent.click(screen.getByRole("button", { name: "Solicitar recuperação" })); expect(await screen.findByRole("alert")).toHaveTextContent("Serviço indisponível"); expect(screen.queryByText(/você receberá/)).not.toBeInTheDocument();
});
it("não envia reset sem token", () => { render(<MemoryRouter><PasswordRecoveryPage reset /></MemoryRouter>); expect(screen.getByRole("button", { name: "Redefinir senha" })).toBeDisabled(); });

it("consome outro link na mesma aba e limpa o fragmento sem manter sucesso antigo", async () => {
  globalThis.history.replaceState({}, "", "/password-reset#token=primeiro-link");
  render(<MemoryRouter><PasswordRecoveryPage reset /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Nova senha"), {target:{value:"frase-segura-nova"}});
  fireEvent.change(screen.getByLabelText("Confirmar nova senha"), {target:{value:"frase-segura-nova"}});
  fireEvent.click(screen.getByRole("button", {name:"Redefinir senha"}));
  await screen.findByText(/Senha redefinida/);
  globalThis.history.replaceState({}, "", "/password-reset#token=segundo-link");
  fireEvent(window, new HashChangeEvent("hashchange"));
  expect(screen.queryByText(/Senha redefinida/)).not.toBeInTheDocument();
  expect(globalThis.location.hash).toBe("");
  expect(screen.getByLabelText("Nova senha")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("Nova senha"), {target:{value:"outra-frase-segura"}});
  fireEvent.change(screen.getByLabelText("Confirmar nova senha"), {target:{value:"outra-frase-segura"}});
  fireEvent.click(screen.getByRole("button", {name:"Redefinir senha"}));
  await waitFor(() => expect(identity.confirmRecovery).toHaveBeenLastCalledWith("segundo-link", "outra-frase-segura"));
});

it("resposta atrasada do link anterior nao sobrescreve o novo formulario", async () => {
  let complete!: () => void;
  vi.mocked(identity.confirmRecovery).mockReturnValueOnce(new Promise<void>(resolve => {complete=resolve;}));
  globalThis.history.replaceState({}, "", "/password-reset#token=anterior");
  render(<MemoryRouter><PasswordRecoveryPage reset /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Nova senha"), {target:{value:"frase-segura-nova"}});
  fireEvent.change(screen.getByLabelText("Confirmar nova senha"), {target:{value:"frase-segura-nova"}});
  fireEvent.click(screen.getByRole("button", {name:"Redefinir senha"}));
  globalThis.history.replaceState({}, "", "/password-reset#token=atual");
  fireEvent(window, new HashChangeEvent("hashchange"));
  await act(async()=>complete());
  expect(screen.queryByText(/Senha redefinida/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", {name:"Redefinir senha"})).toBeEnabled();
  expect(globalThis.location.hash).toBe("");
});


it("preserva o token somente em memoria durante efeitos duplicados do StrictMode", async () => {
  globalThis.history.replaceState({}, "", "/password-reset#token=token-memoria");
  render(<StrictMode><MemoryRouter><PasswordRecoveryPage reset /></MemoryRouter></StrictMode>);
  expect(globalThis.location.hash).toBe("");
  expect(screen.queryByText(/Link ausente/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Nova senha"), {target:{value:"frase-segura-nova"}});
  fireEvent.change(screen.getByLabelText("Confirmar nova senha"), {target:{value:"frase-segura-nova"}});
  fireEvent.click(screen.getByRole("button", {name:"Redefinir senha"}));
  await waitFor(() => expect(identity.confirmRecovery).toHaveBeenCalledWith("token-memoria", "frase-segura-nova"));
});

it("troca entre solicitar e redefinir sem reaproveitar o sucesso da outra etapa", async () => {
  vi.mocked(identity.requestRecovery).mockResolvedValue(undefined);
  globalThis.history.replaceState({}, "", "/password-recovery");
  const view = render(<MemoryRouter><PasswordRecoveryPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("E-mail"), {target:{value:"conta@example.test"}});
  fireEvent.click(screen.getByRole("button", {name:"Solicitar recuperação"}));
  await screen.findByText(/Se a conta for elegível/);
  view.rerender(<MemoryRouter><PasswordRecoveryPage reset /></MemoryRouter>);
  expect(screen.queryByText(/Senha redefinida/)).not.toBeInTheDocument();
  expect(screen.getByText(/Link ausente/)).toBeInTheDocument();
  expect(screen.getByRole("button", {name:"Redefinir senha"})).toBeDisabled();
});
