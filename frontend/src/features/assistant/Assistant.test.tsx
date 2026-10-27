import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { useAuth } from "../auth/hooks/useAuth";
import { Assistant } from "./Assistant";
import { askAssistant, type AssistantReply } from "./assistantApi";

vi.mock("../auth/hooks/useAuth");
vi.mock("./assistantApi", () => ({ askAssistant: vi.fn(), assistantErrorMessage: () => "Não foi possível responder agora. Tente novamente." }));
const user = { id: "synthetic-user", name: "Pessoa de teste", role: "ADMIN", active: true };
const REPLY: AssistantReply = { source: "GROQ", answer: "O pedido foi entregue integralmente.", facts: [], links: [], suggestions: [] };
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user } as ReturnType<typeof useAuth>);
  vi.mocked(askAssistant).mockResolvedValue(REPLY);
});
function RouteJump() {
  const navigate = useNavigate();
  return <button onClick={() => navigate("/orders")}>Ir para Pedidos</button>;
}
function show(path = "/planning/11111111-1111-4111-8111-111111111111") {
  return render(<MemoryRouter initialEntries={[path]}><RouteJump /><Assistant /></MemoryRouter>);
}
function open() { const button = screen.getByRole("button", { name: "Perguntar ao LoadX" }); button.focus(); fireEvent.click(button); }
function send() { fireEvent.change(screen.getByLabelText("Sua pergunta"), { target: { value: "Quantos pedidos entregues?" } }); fireEvent.click(screen.getByRole("button", { name: "Enviar pergunta" })); }

it.each(["DRIVER", "CUSTOM"])("oculta assistente de %s", (role) => {
  vi.mocked(useAuth).mockReturnValue({ user: { ...user, role } } as ReturnType<typeof useAuth>);
  show(); expect(screen.queryByRole("button", { name: "Perguntar ao LoadX" })).not.toBeInTheDocument();
});
it.each(["ADMIN", "LOGISTICS_MANAGER", "CHECKER"])("permite abrir assistente de %s sem consulta automática", (role) => {
  vi.mocked(useAuth).mockReturnValue({ user: { ...user, role } } as ReturnType<typeof useAuth>);
  show(); open(); expect(screen.getByRole("dialog")).toBeInTheDocument(); expect(askAssistant).not.toHaveBeenCalled();
});
it("envia contexto de rota, identifica Groq real e fecha com Escape", async () => {
  show(); open(); send();
  expect(await screen.findByText(REPLY.answer)).toBeInTheDocument();
  expect(screen.getByText("Assistente LoadX · IA real (Groq)")).toBeInTheDocument();
  expect(askAssistant).toHaveBeenCalledWith("Quantos pedidos entregues?", [], { planId: "11111111-1111-4111-8111-111111111111" }, expect.any(AbortSignal));
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Perguntar ao LoadX" })).toHaveFocus();
});
it("exibe fallback honestamente e mantém fatos legíveis sem JSON ou links externos", async () => {
  vi.mocked(askAssistant).mockResolvedValue({ ...REPLY, source: "FALLBACK", facts: [{ name: "Pedido autorizado", criteria: "Situação atual", timezone: "UTC", period_start: null, period_end: null, values: { situacao: "DELIVERED" } }], links: [{ label: "Não autorizado", href: "https://example.com" }] });
  show(); open(); send();
  expect(await screen.findByText("Resumo automático · IA indisponível")).toBeInTheDocument();
  expect(screen.getByText("Entregue")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Não autorizado" })).not.toBeInTheDocument();
});
it("falha permite tentar novamente e não expõe mensagem técnica", async () => {
  vi.mocked(askAssistant).mockRejectedValueOnce(new Error("private-provider-message"));
  show(); open(); send();
  expect(await screen.findByRole("alert")).not.toHaveTextContent("private-provider-message");
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText(REPLY.answer)).toBeInTheDocument();
});
it("bloqueia cliques duplicados e ignora resposta após fechar", async () => {
  let resolve!: (reply: AssistantReply) => void;
  vi.mocked(askAssistant).mockReturnValue(new Promise((done) => { resolve = done; }));
  show(); open(); send();
  expect(screen.getByRole("button", { name: "Consultando…" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Minimizar assistente" }));
  resolve(REPLY);
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  open(); expect(screen.queryByText(REPLY.answer)).not.toBeInTheDocument(); expect(askAssistant).toHaveBeenCalledTimes(1);
});

it("mostra registros cancelados com rótulos legíveis e navegação real", async () => {
  const href = "/planning/distributions/22222222-2222-4222-8222-222222222222";
  vi.mocked(askAssistant).mockResolvedValue({ ...REPLY, facts: [{ name: "Distribuições canceladas", criteria: "Criadas no período", timezone: "UTC", period_start: null, period_end: null, values: { currently_canceled_distributions_created_in_period: 1 }, links: [{ label: "Distribuição criada em 26/10/2026", href }] }] });
  show(); open(); send();
  expect(await screen.findByText("Distribuições canceladas criadas no período")).toBeInTheDocument();
  const link = screen.getByRole("link", { name: "Distribuição criada em 26/10/2026" });
  expect(link).toHaveAttribute("href", href);
  fireEvent.click(link);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("abre ajuda de falha com pergunta preparada sem enviar automaticamente", () => {
  show("/planning");
  fireEvent(window, new CustomEvent("loadx:assistant", { detail: { question: "Como resolver uma falha sem perder o trabalho salvo?" } }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(screen.getByLabelText("Sua pergunta")).toHaveValue("Como resolver uma falha sem perder o trabalho salvo?");
  expect(askAssistant).not.toHaveBeenCalled();
});

it("exige seleção explícita de cliente ambíguo e conserva filtro visível", async () => {
  const reference = "33333333-3333-4333-8333-333333333333";
  vi.mocked(askAssistant).mockResolvedValue({ ...REPLY, facts: [{ name: "Seleção de cliente", criteria: "Selecione um cliente", timezone: "UTC", period_start: null, period_end: null, values: { result: "ambiguous_customer" }, choices: [{ reference, label: "Cliente Operacional — Outra cidade/SP" }] }] });
  show(); open(); send();
  fireEvent.click(await screen.findByRole("button", { name: "Selecionar Cliente Operacional — Outra cidade/SP" }));
  expect(askAssistant).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Cliente: Cliente Operacional — Outra cidade/SP")).toBeInTheDocument();
  expect(screen.getByLabelText("Sua pergunta")).toHaveValue("Quantos pedidos entregues?");
  fireEvent.click(screen.getByRole("button", { name: "Enviar pergunta" }));
  await waitFor(() => expect(askAssistant).toHaveBeenCalledTimes(2));
  expect(vi.mocked(askAssistant).mock.calls[1][2].customerId).toBe(reference);
});


it("envia diagnóstico separado do plano da rota e sem consulta automática", async () => {
  show();
  const receipt = "opaque-signed-receipt";
  fireEvent(window, new CustomEvent("loadx:assistant", { detail: { diagnosticToken: receipt, question: "Por que falhou?" } }));
  await screen.findByRole("dialog");
  expect(askAssistant).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Enviar pergunta" }));
  await waitFor(() => expect(askAssistant).toHaveBeenCalledOnce());
  expect(vi.mocked(askAssistant).mock.calls[0][2]).toEqual({ diagnosticToken: receipt });
});

it("mantém histórico ao navegar e ao minimizar sem bloquear a tela", async () => {
  show();
  open(); send();
  expect(await screen.findByText(REPLY.answer)).toBeInTheDocument();
  expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "false");
  fireEvent.click(screen.getByRole("button", { name: "Ir para Pedidos" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(screen.getByText(REPLY.answer)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Minimizar assistente" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  open();
  expect(screen.getByText(REPLY.answer)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Sua pergunta"), { target: { value: "Quais pedidos estão prontos?" } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar pergunta" }));
  await waitFor(() => expect(vi.mocked(askAssistant).mock.calls.length).toBe(2));
  expect(vi.mocked(askAssistant).mock.calls[1][2]).toEqual({});
});
