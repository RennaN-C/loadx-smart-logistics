import { useEffect, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { explainLoadPlan, type PlanAIExplanationResult } from "../api/loadPlansApi";

/** Optional, read-only explanation. Never calls optimization or mutates a plan. */
export function PlanAIExplanation({ planId }: { readonly planId: string }) {
  const [result, setResult] = useState<PlanAIExplanationResult | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    setResult(null);
    setError(false);
    setWorking(false);
  }, [planId]);

  async function explain() {
    if (working) return;
    setWorking(true);
    setError(false);
    try {
      const response = await explainLoadPlan(planId);
      if (response.loadPlanId === planId) setResult(response);
      else setError(true);
    } catch {
      setError(true);
    } finally {
      setWorking(false);
    }
  }

  return <section className="plan-ai-explanation" aria-label="Assistente de IA para o plano">
    <h3>Assistente de IA — entenda o resultado</h3>
    <p>O posicionamento e a distribuição já foram calculados pelas regras físicas do LoadX.
      A explicação é uma etapa opcional, independente do cálculo e da aprovação.</p>
    {result ? <div className="plan-ai-result" role="status">
      <strong>{result.source === "AI" ? "Explicação gerada por IA" : "Resumo automático (IA indisponível)"}</strong>
      <p>{result.explanation}</p>
    </div> : null}
    {error ? <AlertBanner>Não foi possível consultar a explicação agora. O plano já calculado continua salvo e não foi alterado.</AlertBanner> : null}
    <div className="entity-form-actions">
      <button type="button" className="btn-secondary" disabled={working}
        onClick={() => void explain()}>{working ? "Preparando explicação…" : result ? "Atualizar explicação" : "Solicitar explicação do plano"}</button>
    </div>
  </section>;
}
