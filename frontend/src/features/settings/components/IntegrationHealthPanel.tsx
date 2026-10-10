import { useEffect, useState } from "react";
import { ApiError } from "../../../types/api";
import { getIntegrationHealth, type ComponentHealth, type HealthComponent, type HealthReason, type HealthStatus, type IntegrationHealthReport } from "../api/integrationHealthApi";
import "./IntegrationHealthPanel.css";

const COMPONENTS: Record<HealthComponent, { title: string; description: string }> = {
  api: { title: "API LoadX", description: "Liveness compartilhada com /health: o serviço respondeu à consulta." },
  database: { title: "Banco e migrations", description: "Readiness existente de /ready: acesso ao PostgreSQL e revision Alembic." },
  whatsapp: { title: "WhatsApp", description: "Nesta fase, a saída é simulada. Não há conexão, envio ou confirmação de entrega pela Meta." },
  ai: { title: "Inteligência artificial", description: "Disponibilidade real exige adapter aprovado e configurado. O painel não executa prompts nem implementa o provider." },
  webhook: { title: "Webhook interno", description: "Recebimento HTTP autenticado pertence à OC83. O simulador de mensagens não é um webhook." },
  notifications: { title: "Notificações internas", description: "A base existente trata início de viagem e ocorrência após commit, com saída WhatsApp simulada. A evolução é da OC84." },
};
const STATUSES: Record<HealthStatus, string> = { AVAILABLE: "DISPONÍVEL", SIMULATED: "SIMULADO", NOT_CONFIGURED: "NÃO CONFIGURADO", NOT_IMPLEMENTED: "NÃO IMPLEMENTADO", LIMITED: "LIMITADO", UNAVAILABLE: "FALHA", TIMEOUT: "TEMPO ESGOTADO" };
const REASONS: Record<HealthReason, string> = {
  LIVE: "Liveness disponível.", READY: "Verificação disponível.", READINESS_FAILED: "Readiness indisponível; detalhes internos foram omitidos.", TIMEOUT: "A consulta excedeu o limite de espera.", MOCK_PROVIDER: "Provider local simulado, sem serviço externo.", PROVIDER_NOT_IMPLEMENTED: "Nenhum adapter externo aprovado está implementado nesta base.", OC83_PENDING: "Aguardando implementação da OC83.", OC84_PENDING: "Escopo interno atual limitado; OC84 ainda pendente.", NOT_CONFIGURED: "O componente não está configurado.", APPROVAL_REQUIRED: "Ativação real depende de aprovação.", PROVIDER_FAILED: "Não foi possível obter o sinal do componente.", INVALID_SIGNAL: "O componente retornou um sinal incompatível com a política aprovada.",
};
function HealthCard({ item }: { readonly item: ComponentHealth }) {
  const metadata = COMPONENTS[item.component];
  let configuration = "Não verificada";
  if (item.configured !== null) configuration = item.configured ? "Presente" : "Ausente";
  return <li className="integration-health-card">
    <h3>{metadata.title}</h3>
    <span className="integration-health-badge" data-status={item.status}>{STATUSES[item.status]}</span>
    <p>{metadata.description}</p>
    <dl><div><dt>Modo</dt><dd>{{ INTERNAL: "Interno", MOCK: "Simulado", REAL: "Real (sujeito à configuração e aprovação)" }[item.mode]}</dd></div><div><dt>Configuração</dt><dd>{configuration}</dd></div></dl>
    <p>{REASONS[item.reason_code]}</p>
  </li>;
}
function failureMessage(error_: unknown): string {
  if (error_ instanceof ApiError && error_.status === 403) return "A consulta de integrações é exclusiva do ADMIN.";
  if (error_ instanceof ApiError && error_.status === 401) return "Sua sessão não permite consultar as integrações. Entre novamente.";
  return "Não foi possível consultar integrações e saúde. A API pode estar indisponível ou ter excedido o tempo de resposta.";
}
export function IntegrationHealthPanel() {
  const [report, setReport] = useState<IntegrationHealthReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(null);
    getIntegrationHealth().then((result) => { if (active) setReport(result); })
      .catch((error_: unknown) => {
        if (!active) return;
        setError(failureMessage(error_));
        if (error_ instanceof ApiError && (error_.status === 401 || error_.status === 403)) setReport(null);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refresh]);
  return <div className="integration-health-panel" aria-busy={loading}>
    <p>Diagnóstico atual, somente para consulta. Atualizar não envia mensagens, executa prompts ou modifica configurações.</p>
    <button type="button" className="btn-secondary" disabled={loading} onClick={() => setRefresh((value) => value + 1)}>{loading ? "Consultando…" : "Atualizar estados"}</button>
    {loading && <output className="integration-health-feedback">Carregando integrações e saúde…</output>}
    {error && <p role="alert">{error}</p>}
    {report && <>
      {error && <p>Exibindo a última consulta bem-sucedida; os dados abaixo podem estar desatualizados.</p>}
      <p><strong>{report.overall_status === "DEGRADED" ? "Saúde degradada: há falha ou timeout." : "Cobertura parcial: há componentes simulados, limitados ou pendentes."}</strong></p>
      <p>Consulta em <time dateTime={report.checked_at}>{new Date(report.checked_at).toLocaleString("pt-BR")}</time></p>
      {report.components.length ? <ul className="integration-health-grid">{report.components.map((item) => <HealthCard key={item.component} item={item} />)}</ul> : <p>Nenhum indicador foi disponibilizado nesta consulta.</p>}
      <p className="integration-health-reference">Referência do diagnóstico: <code>{report.correlation_id}</code>. Falhas desta consulta podem ser correlacionadas aos eventos operacionais sanitizados. Histórico persistente de integrações não está disponível nesta etapa.</p>
    </>}
  </div>;
}
