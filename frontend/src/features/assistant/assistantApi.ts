import { ApiError } from "../../types/api";
import { api, toApiError } from "../../services/api";

export interface AssistantContext { planId?: string; distributionId?: string }
export interface ChatMessage { role: "user" | "assistant"; content: string }
export interface AssistantFact {
  name: string; criteria: string; period_start: string | null; period_end: string | null;
  links?: { label: string; href: string }[];
  timezone: string; values: Record<string, number | string | null>;
}
export interface AssistantReply {
  source: "GROQ" | "FALLBACK"; answer: string; facts: AssistantFact[];
  suggestions: string[]; links: { label: string; href: string }[];
}
export async function askAssistant(message: string, history: ChatMessage[], context: AssistantContext, signal?: AbortSignal): Promise<AssistantReply> {
  try {
    const { data } = await api.post<AssistantReply>("/assistant/messages", {
      message, history: history.slice(-8), plan_id: context.planId, distribution_id: context.distributionId,
    }, { signal, timeout: 25_000 });
    return data;
  } catch (error) { throw toApiError(error); }
}
export interface AssistantOpenContext extends AssistantContext { question?: string }
export function openAssistant(context: AssistantOpenContext) {
  window.dispatchEvent(new CustomEvent<AssistantContext>("loadx:assistant", { detail: context }));
}

export function assistantErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === "ASSISTANT_CONTEXT_MISMATCH") return "O planejamento foi atualizado. Reabra o registro pela lista e tente novamente.";
  const messages: Record<number, string> = {
    401: "Sua sessão expirou. Entre novamente para consultar o assistente.",
    403: "Seu perfil não tem permissão para esta consulta. As permissões da operação continuam preservadas.",
    404: "Não foi possível localizar o planejamento. Volte à lista e abra um registro existente.",
    422: "Revise sua pergunta e o período informado. As consultas aceitam até 93 dias.",
    429: "Aguarde um instante antes de perguntar novamente. Há uma consulta em andamento ou o limite temporário foi atingido.",
  };
  return error instanceof ApiError && error.status && messages[error.status] ? messages[error.status] : "Não foi possível responder agora. Verifique sua conexão e tente novamente; nenhum registro foi alterado.";
}
