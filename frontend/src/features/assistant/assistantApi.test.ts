import { expect, it, vi } from "vitest";
import { api } from "../../services/api";
import { ApiError } from "../../types/api";
import { askAssistant, assistantErrorMessage, openAssistant, type ChatMessage } from "./assistantApi";

vi.mock("../../services/api", () => ({ api: { post: vi.fn() }, toApiError: (error: unknown) => error }));
it("envia contexto referencial e histórico limitado pelo cliente CSRF existente", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { source: "FALLBACK", answer: "Resumo", facts: [], links: [], suggestions: [] } });
  const history: ChatMessage[] = Array.from({ length: 12 }, (_, index) => ({ role: "user", content: `Pergunta ${index}` }));
  const controller = new AbortController();
  await askAssistant("Pergunta", history, { planId: "persisted-plan" }, controller.signal);
  expect(api.post).toHaveBeenCalledWith("/assistant/messages", { message: "Pergunta", diagnostic_token: undefined, customer_id: undefined, history: history.slice(-8), plan_id: "persisted-plan", distribution_id: undefined }, { signal: controller.signal, timeout: 25_000 });
});
it("erros do servidor não expõem mensagens privadas e distinguem contexto atualizado", () => {
  for (const status of [401, 403, 404, 422, 429, 500]) expect(assistantErrorMessage(new ApiError("SERVER_ERROR", "private-provider-trace", [], status))).not.toContain("private-provider-trace");
  expect(assistantErrorMessage(new ApiError("ASSISTANT_CONTEXT_MISMATCH", "private"))).toContain("planejamento foi atualizado");
});
it("ação contextual apenas prepara abertura, sem enviar pergunta", () => {
  const listener = vi.fn(); window.addEventListener("loadx:assistant", listener);
  const context = { planId: "persisted-plan", question: "Como continuar?" };
  openAssistant(context);
  expect(listener.mock.calls[0][0].detail).toEqual(context);
  window.removeEventListener("loadx:assistant", listener);
});
