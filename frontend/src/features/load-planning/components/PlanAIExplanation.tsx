import { openAssistant } from "../../assistant/assistantApi";

/** Context is resolved again by the backend; this button never calculates. */
export function PlanAIExplanation({ planId }: { readonly planId: string }) {
  return <button type="button" className="btn-secondary" onClick={() => openAssistant({ planId })}>Perguntar ao LoadX sobre esta carga</button>;
}
