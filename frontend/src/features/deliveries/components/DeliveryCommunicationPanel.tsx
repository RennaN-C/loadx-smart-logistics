import { useEffect, useState } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { ApiError, type Page } from "../../../types/api";
import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import { listDeliveryCommunications, type DeliveryCommunication, type ProcessingStatus, type SimulationStatus } from "../api/communicationsApi";
import "./DeliveryEvidencePanel.css";

const SIMULATION: Record<SimulationStatus, string> = { NOT_ATTEMPTED: "Sem tentativa", ATTEMPT_CLAIMED: "Tentativa em andamento", SIMULATED: "Simulado", FAILED: "Simulação falhou", NO_RECIPIENT: "Sem destinatário" };
const PROCESSING: Record<ProcessingStatus, string> = { PENDING: "Pendente", PROCESSING: "Processando", SUCCEEDED: "Concluído no simulador", RETRYABLE: "Aguardando nova tentativa", TERMINAL: "Processamento encerrado", UNCERTAIN: "Resultado incerto" };
const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

export function DeliveryCommunicationPanel({ deliveryId }: { readonly deliveryId: string }) { return <CommunicationContent key={deliveryId} deliveryId={deliveryId} />; }
function CommunicationContent({ deliveryId }: { readonly deliveryId: string }) {
  const [page, setPage] = useState(1);
  const [reload, setReload] = useState(0);
  const [data, setData] = useState<Page<DeliveryCommunication> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true; setLoading(true); setError(""); setData(null);
    void listDeliveryCommunications(deliveryId, { page, pageSize: 20 }).then(result => { if (active) setData(result); }).catch(e => {
      if (active) setError(fallbackErrorMessage(e instanceof ApiError ? e : new ApiError("NETWORK_ERROR", "Falha na consulta.")));
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [deliveryId, page, reload]);
  return <section className="delivery-communications" aria-label="Comunicação da entrega" aria-busy={loading}>
    <div className="evidence-list-header"><StatusPill tone="neutral">WhatsApp simulado</StatusPill><button type="button" className="btn-secondary" disabled={loading} onClick={() => setReload(n => n + 1)}>Atualizar comunicação</button></div>
    <p>Registros reais vinculados às ocorrências desta entrega. O canal é simulado: não comprova envio, recebimento ou leitura no WhatsApp da Meta.</p>
    {loading && <p role="status">Consultando comunicação…</p>}
    {error && <><AlertBanner>{error}</AlertBanner><button type="button" className="btn-secondary" onClick={() => setReload(n => n + 1)}>Tentar novamente</button></>}
    {data && <>{!data.items.length ? <p className="entity-state">Nenhuma comunicação operacional vinculada a esta entrega.</p> : <ul className="evidence-list">{data.items.map(item => <li key={item.id} className="evidence-item">
      <div className="evidence-item-head"><strong>Ocorrência {item.occurrence_id.slice(0, 8)}</strong><time dateTime={item.created_at}>{dateTime.format(new Date(item.created_at))}</time></div>
      <dl className="communication-status"><div><dt>Simulação</dt><dd>{SIMULATION[item.simulation_status]}</dd></div><div><dt>Processamento</dt><dd>{item.processing_status ? PROCESSING[item.processing_status] : "Sem fila registrada"}</dd></div></dl>
    </li>)}</ul>}<Pagination page={data.page} totalPages={data.totalPages} onChange={setPage} label="comunicação" /></>}
    <details className="communication-limits"><summary>O que esta consulta inclui</summary><p>Somente notificações de ocorrências associadas pelo servidor a esta entrega. Eventos gerais da viagem e notificações pessoais não são apresentados como conversa. Envio livre de mensagens e canais reais não estão disponíveis.</p></details>
  </section>;
}
