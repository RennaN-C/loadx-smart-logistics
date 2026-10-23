import { useEffect, useState } from "react";
import { Icon, type IconName } from "../../../components/Icon";
import { ApiError } from "../../../types/api";
import { getIntegrationHealth, type ComponentHealth, type HealthComponent, type HealthReason, type HealthStatus, type IntegrationHealthReport } from "../api/integrationHealthApi";
import "./IntegrationHealthPanel.css";

const COMPONENTS: Record<HealthComponent, { title: string; description: string }> = {
  api: { title: "API LoadX", description: "Confirma que o serviço está respondendo; não verifica todas as operações." },
  database: { title: "Banco de dados", description: "Verifica a conexão e se a estrutura do banco está atualizada." },
  whatsapp: { title: "WhatsApp", description: "Não há conexão, envio ou confirmação de entrega pela Meta. O funcionamento é simulado." },
  ai: { title: "Inteligência artificial", description: "Indica o modo de funcionamento e a configuração do provedor aprovado." },
  webhook: { title: "Webhook interno", description: "Recebimento interno de eventos, conforme a configuração deste ambiente. Não comprova conexão externa." },
  notifications: { title: "Notificações internas", description: "Eventos persistidos e central de notificações. O processamento em segundo plano tem verificação separada." },
};
const STATUSES: Record<HealthStatus, string> = { AVAILABLE: "DISPONÍVEL", SIMULATED: "SIMULADO", NOT_CONFIGURED: "NÃO CONFIGURADO", NOT_IMPLEMENTED: "NÃO IMPLEMENTADO", LIMITED: "LIMITADO", UNAVAILABLE: "FALHA", TIMEOUT: "TEMPO ESGOTADO" };
const REASONS: Record<HealthReason, string> = {
  LIVE: "O serviço está respondendo.",
  READY: "A verificação de disponibilidade foi concluída.",
  READINESS_FAILED: "A conexão ou a estrutura do banco não está pronta. Detalhes internos foram omitidos.",
  TIMEOUT: "A consulta excedeu o tempo de espera.",
  MOCK_PROVIDER: "Funcionamento simulado, sem comunicação com um serviço externo.",
  PROVIDER_NOT_IMPLEMENTED: "Nenhum provedor externo aprovado está disponível nesta versão.",
  OC83_PENDING: "Diagnóstico de uma versão anterior. Atualize a consulta para conferir a configuração atual.",
  OC84_PENDING: "Diagnóstico de uma versão anterior. Atualize a consulta para conferir as limitações atuais.",
  NOT_CONFIGURED: "O componente não está configurado neste ambiente.",
  RUNTIME_CONFIGURED: "O componente interno foi inicializado. Isso não comprova envio ou recebimento por um serviço externo.",
  WORKER_NOT_OBSERVED: "A infraestrutura de notificações está implementada. Esta consulta não verifica se o processador de eventos está ativo nem se há eventos aguardando processamento.",
  APPROVAL_REQUIRED: "A ativação real depende de aprovação.",
  PROVIDER_FAILED: "Não foi possível verificar o componente.",
  INVALID_SIGNAL: "A resposta do componente não permite confirmar sua disponibilidade.",
};
const COMPONENT_ICONS: Record<HealthComponent, IconName> = { api: "gauge", database: "orders", whatsapp: "users", ai: "planning", webhook: "settings", notifications: "report" };
function HealthCard({ item }: { readonly item: ComponentHealth }) {
  const metadata = COMPONENTS[item.component];
  let configuration = "Não verificada";
  if (item.configured !== null) configuration = item.configured ? "Presente" : "Ausente";
  return <li className="integration-health-card">
    <div className="integration-health-card-header"><Icon name={COMPONENT_ICONS[item.component]} size={20} /><h3>{metadata.title}</h3><span className="integration-health-badge" data-status={item.status}>{STATUSES[item.status]}</span></div>
    <p className="integration-health-context">{{ api: "Serviço da aplicação", database: "Persistência e integridade", whatsapp: "Mensagens operacionais", ai: "Apoio ao planejamento", webhook: "Entrada de eventos", notifications: "Comunicação interna" }[item.component]}</p>
    <details className="integration-health-details"><summary>Escopo e limites</summary><p className="integration-health-reason">{REASONS[item.reason_code]}</p><dl><div><dt>Modo</dt><dd>{{ INTERNAL: "Interno", MOCK: "Simulado", REAL: "Real (sujeito à configuração e aprovação)" }[item.mode]}</dd></div><div><dt>Configuração</dt><dd>{configuration}</dd></div></dl>
    <p>{metadata.description}</p></details>
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
    <div className="integration-health-toolbar"><p>Estado das integrações<span>Consulta somente leitura, sem executar ações nos serviços.</span></p><button type="button" className="btn-secondary" disabled={loading} onClick={() => setRefresh((value) => value + 1)}>{loading ? "Consultando…" : "Atualizar estados"}</button></div>
    {loading && <output className="integration-health-feedback"><span className="spinner" aria-hidden="true" /><span>Carregando integrações e saúde…</span></output>}
    {error && <p role="alert" className="integration-health-error">{error}</p>}
    {report && <>
      {error && <p className="integration-health-stale">Exibindo a última consulta bem-sucedida; os dados abaixo podem estar desatualizados.</p>}
      <div className="integration-health-summary" data-status={report.overall_status}><strong>{report.overall_status === "DEGRADED" ? "Saúde degradada: há falha ou demora na resposta." : "Há serviços simulados ou com verificação limitada."}</strong><p>Consulta em <time dateTime={report.checked_at}>{new Date(report.checked_at).toLocaleString("pt-BR")}</time></p></div>
      {report.components.length ? <ul className="integration-health-grid">{report.components.map((item) => <HealthCard key={item.component} item={item} />)}</ul> : <p className="integration-health-empty">Nenhum indicador foi disponibilizado nesta consulta.</p>}
      <details className="integration-health-reference"><summary>Referência do diagnóstico</summary><p><code>{report.correlation_id}</code>. Falhas desta consulta podem ser correlacionadas aos eventos operacionais sanitizados. Histórico persistente de integrações não está disponível nesta etapa.</p></details>
    </>}
  </div>;
}
