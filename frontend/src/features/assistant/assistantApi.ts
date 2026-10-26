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
export function openAssistant(context: AssistantContext) {
  window.dispatchEvent(new CustomEvent<AssistantContext>("loadx:assistant", { detail: context }));
}
