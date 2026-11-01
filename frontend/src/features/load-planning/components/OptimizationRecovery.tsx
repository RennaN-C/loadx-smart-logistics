import { useState } from "react";
import { Link } from "react-router-dom";
import "./OptimizationRecovery.css";

interface Props {
  readonly count: number;
  readonly working: boolean;
  readonly onConsult: () => void;
  readonly onRetry: () => void;
  readonly canDiscard: boolean;
  readonly onDiscard: () => void;
}
export function OptimizationRecovery({ count, working, onConsult, onRetry, canDiscard, onDiscard }: Props) {
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  return <section className="optimization-recovery" aria-label="Retomar otimização" aria-busy={working}>
    <h2>Confirme a otimização anterior</h2>
    <p>Há uma solicitação de {count} {count === 1 ? "pedido" : "pedidos"} aguardando confirmação nesta aba.
      Consulte o servidor antes de iniciar outra distribuição. Esta referência local não comprova que um plano foi salvo.</p>
    <div className="optimization-recovery-actions">
      <button type="button" className="btn-primary" disabled={working} onClick={onConsult}>{working ? "Consultando…" : "Consultar resultado salvo"}</button>
      <button type="button" className="btn-secondary" disabled={working} onClick={onRetry}>Repetir solicitação original</button>
      <Link className="optimization-recovery-link" to="/planning">Ver planos existentes</Link>
      {canDiscard ? <button type="button" className="btn-secondary" disabled={working}
        onClick={() => setConfirmDiscard(true)}>Encerrar tentativa sem resultado</button> : null}
    </div>
    {canDiscard ? <p role="status" className="entity-form-help">O servidor confirmou que não encontrou um resultado salvo para esta solicitação.
      Você pode encerrar o acompanhamento LOCAL e iniciar um novo planejamento após verificar os planos existentes.</p> : null}
    {canDiscard && confirmDiscard ? <div className="optimization-recovery-confirm" role="group" aria-label="Confirmar encerramento da tentativa">
      <p>Encerrar apenas o acompanhamento desta tentativa nesta aba? Nenhum pedido ou plano será excluído do servidor.
        Confira os planos existentes antes de começar outra otimização.</p>
      <div className="optimization-recovery-actions">
        <button type="button" className="btn-secondary" disabled={working} onClick={() => setConfirmDiscard(false)}>Manter tentativa</button>
        <button type="button" className="btn-primary" disabled={working} onClick={onDiscard}>Confirmar e voltar ao planejamento</button>
      </div>
    </div> : null}
    <p className="entity-form-help">A repetição usa a mesma identidade e os pedidos originais. Se o servidor ainda estiver calculando, aguarde e consulte novamente.</p>
  </section>;
}
