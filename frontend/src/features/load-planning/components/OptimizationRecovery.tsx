import { Link } from "react-router-dom";
import "./OptimizationRecovery.css";

interface Props {
  readonly count: number;
  readonly working: boolean;
  readonly onConsult: () => void;
  readonly onRetry: () => void;
}
export function OptimizationRecovery({ count, working, onConsult, onRetry }: Props) {
  return <section className="optimization-recovery" aria-label="Retomar otimização" aria-busy={working}>
    <h2>Confirme a otimização anterior</h2>
    <p>Há uma solicitação de {count} {count === 1 ? "pedido" : "pedidos"} aguardando confirmação nesta aba.
      Consulte o servidor antes de iniciar outra distribuição. Esta referência local não comprova que um plano foi salvo.</p>
    <div className="optimization-recovery-actions">
      <button type="button" className="btn-primary" disabled={working} onClick={onConsult}>{working ? "Consultando…" : "Consultar resultado salvo"}</button>
      <button type="button" className="btn-secondary" disabled={working} onClick={onRetry}>Repetir solicitação original</button>
      <Link className="optimization-recovery-link" to="/planning">Ver planos existentes</Link>
    </div>
    <p className="entity-form-help">A repetição usa a mesma identidade e os pedidos originais. Se o servidor ainda estiver calculando, aguarde e consulte novamente.</p>
  </section>;
}
