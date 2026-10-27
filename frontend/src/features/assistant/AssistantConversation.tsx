import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { PLAN_STATUS_LABELS, REJECTION_LABELS } from "../load-planning/components/loadPlanLabels";
import type { AssistantFact, AssistantReply, CustomerChoice } from "./assistantApi";

const LABELS: Record<string, string> = {
  ...PLAN_STATUS_LABELS, ...REJECTION_LABELS,
  DRAFT: "Rascunho", READY: "Pronto para coleta", PLANNED: "Planejado", IN_TRANSIT: "Em trânsito", DELIVERED: "Entregue", CANCELED: "Cancelado",
  PROPOSED: "Proposta", PARTIALLY_APPROVED: "Parcialmente aprovada", INCOMPLETE: "Incompleta",
  DISTRIBUTION_CAPACITY_INSUFFICIENT: "Capacidade insuficiente nesta tentativa",
  insufficient_data: "Dados insuficientes", ambiguous_customer: "Mais de um cliente encontrado", customer_not_found: "Cliente não encontrado",
};
const FACT_LABELS: Record<string, string> = {
  remaining_volumes: "Volumes sem posição segura",
  unavailable_trucks: "Caminhões inelegíveis nesta tentativa",
  fully_delivered_orders: "Pedidos totalmente entregues",
  dispatched_orders: "Pedidos expedidos distintos",
  completed_delivery_legs: "Pernas de entrega concluídas",
  top_customer_name: "Cliente com mais pedidos entregues",
  top_customer_delivered_orders: "Entregas do cliente líder",
  trips_started: "Viagens iniciadas",
  trips_finished: "Viagens concluídas",
  distinct_trucks_used: "Caminhões utilizados",
  plans_with_started_trip: "Planos com viagem iniciada",
  average_plan_occupancy_percent: "Ocupação média por plano (%)",
  planned_loaded_volumes: "Volumes nos planos",
  planned_rejected_volumes: "Volumes rejeitados",
  planned_loaded_weight_kg: "Peso planejado (kg)",
  currently_canceled_distributions_created_in_period: "Distribuições canceladas criadas no período",
  total_records: "Total de cadastros",
  algorithm_version: "Versão do algoritmo",
  truck_plate: "Placa do caminhão",
  is_current_part: "Parte vigente",
  distribution_status: "Situação da distribuição",
  part_status: "Situação da parte",
  page: "Página",
  total_pages: "Total de páginas",
  page_records: "Registros nesta página",
  page_vehicle_count: "Veículos nesta página",
  page_active_count: "Ativos nesta página",
  page_archived_count: "Arquivados nesta página",
  page_unavailable_count: "Indisponíveis nesta página",
  unavailable_vehicles: "Veículos indisponíveis",
  result: "Resultado",
  bounded_matches: "Correspondências encontradas (limitadas)",
  required_data: "Dados necessários",
  company: "Empresa",
  status: "Situação",
  loaded_volumes: "Volumes carregados",
  rejected_volumes: "Volumes rejeitados",
  occupancy_percent: "Ocupação (%)",
  weight_kg: "Peso (kg)",
  truck_capacity_weight_kg: "Capacidade de peso (kg)",
  internal_width_cm: "Largura interna (cm)",
  internal_height_cm: "Altura interna (cm)",
  internal_length_cm: "Comprimento interno (cm)",
  truck_count: "Caminhões",
  volume_count: "Volumes",
};
const PRIMARY_METRICS = [
  "fully_delivered_orders",
  "currently_canceled_distributions_created_in_period",
  "loaded_volumes",
  "remaining_volumes",
  "rejected_volumes",
  "trips_started",
  "trips_finished",
  "page_unavailable_count",
  "page_vehicle_count",
  "planned_loaded_volumes",
  "dispatched_orders",
] as const;

function readable(value: string): string {
  return LABELS[value] ?? FACT_LABELS[value] ?? (value.startsWith("reason_") ? "Motivo: " + value.slice(7).replaceAll("_", " ").toLowerCase() : value.replaceAll("_", " "));
}
function formatValue(value: string | number | null): string {
  if (value === null) return "Sem dados";
  return typeof value === "number" ? value.toLocaleString("pt-BR") : readable(value);
}
function allowedLink(href: string): boolean {
  return ["/products", "/trucks", "/trucks?tab=availability", "/orders", "/deliveries", "/reports", "/planning"].includes(href)
    || /^\/planning\/(?:distributions\/)?[0-9a-f-]{36}$/i.test(href);
}
function periodLabel(fact: AssistantFact): string | null {
  if (!fact.period_start || !fact.period_end) return null;
  const start = new Date(fact.period_start);
  const end = new Date(fact.period_end);
  if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime())) return null;
  const days = Math.round((end.getTime() - start.getTime()) / 86_400_000);
  if (days === 30) return "Últimos 30 dias";
  return start.toLocaleDateString("pt-BR", { timeZone: "UTC" }) + " a "
    + end.toLocaleDateString("pt-BR", { timeZone: "UTC" }) + " · UTC";
}
function visibleAnswer(reply: Omit<AssistantReply, "facts">, hasMetric: boolean): string {
  if (!hasMetric || (reply.source !== "GROQ" && reply.source !== "BACKEND")) return reply.answer;
  return reply.answer.split(/\n\n+/).filter((paragraph) => {
    const trimmed = paragraph.trim();
    return !trimmed.startsWith("Resultado confirmado pelo LoadX:")
      && trimmed !== "Consultei os registros autorizados. Os detalhes abaixo mostram a origem, os critérios e o período da consulta."
      && trimmed !== "Consultei os registros autorizados do LoadX. Confira os indicadores abaixo para ver os critérios, o período e a origem.";
  }).join("\n\n").trim();
}

export interface Turn {
  readonly id: string;
  question: string;
  reply?: Omit<AssistantReply, "facts"> & { facts: (AssistantFact & { clientKey: string })[] };
}
interface FactProps {
  readonly fact: AssistantFact;
  readonly onLink: () => void;
  readonly onSelectCustomer: (choice: CustomerChoice) => void;
  readonly working: boolean;
}

function Fact({ fact, onLink, onSelectCustomer, working }: FactProps) {
  const primaryKey = PRIMARY_METRICS.find((key) => typeof fact.values[key] === "number");
  const primary = primaryKey ? fact.values[primaryKey] : null;
  const secondary = Object.entries(fact.values).filter(([key, value]) =>
    key !== primaryKey && typeof value === "number" &&
    !["page", "total_pages", "top_customer_delivered_orders", "bounded_matches"].includes(key)
  ).slice(0, 2);
  const customer = fact.values.top_customer_name;
  const hasChoices = Boolean(fact.choices?.length);
  const compact = typeof primary === "number";
  const period = periodLabel(fact);
  return <section className="assistant-result" aria-label={fact.name}>
    {compact ? <>
      <div className="assistant-result-heading"><span>{fact.name}</span>{period ? <span className="assistant-period">{period}</span> : null}</div>
      <div className="assistant-main-metric">
        <strong className="assistant-main-value">{formatValue(primary)}</strong>
        <span>{readable(primaryKey!)}</span>
      </div>
      {secondary.length ? <dl className="assistant-metric-grid">{secondary.map(([key, value]) =>
        <div key={key}><dt>{readable(key)}</dt><dd>{formatValue(value)}</dd></div>
      )}</dl> : null}
      {typeof customer === "string" && customer ? <p className="assistant-customer">Cliente com mais entregas: <strong>{customer}</strong></p> : null}
    </> : <p className="assistant-result-heading">{fact.name}</p>}

    {hasChoices ? <div className="assistant-choice-list" aria-label="Escolher cliente">{fact.choices?.map((choice) =>
      <button type="button" className="btn-secondary" disabled={working} key={choice.reference} onClick={() => onSelectCustomer(choice)}>Selecionar {choice.label}</button>
    )}</div> : null}
    {fact.links?.length ? <nav className="assistant-result-links" aria-label="Registros da consulta">{fact.links.filter((link) => allowedLink(link.href)).map((link) =>
      <Link key={link.href} to={link.href} onClick={onLink}>{link.label}<Icon name="arrow-right" size={15} /></Link>
    )}</nav> : null}
    <details className="assistant-fact" open={compact || Object.keys(fact.values).some((key) => key.startsWith("item_")) ? undefined : true}>
      <summary>{compact ? "Ver critérios e dados completos" : "Informações da consulta"}</summary>
      <div className="assistant-fact-content">
        <p>{fact.criteria}</p>
        {fact.filter_label ? <p>{fact.filter_label}</p> : null}
        {fact.period_start && fact.period_end ? <p>Período (UTC): {new Date(fact.period_start).toLocaleString("pt-BR", { timeZone: "UTC" })} a {new Date(fact.period_end).toLocaleString("pt-BR", { timeZone: "UTC" })} (fim exclusivo).</p> : null}
        <dl>{Object.entries(fact.values).map(([key, value]) =>
          <div key={key}><dt>{readable(key)}</dt><dd>{formatValue(value)}</dd></div>
        )}</dl>
      </div>
    </details>
  </section>;
}

function TurnRow({ turn, onLink, onSelectCustomer, working }: {
  readonly turn: Turn;
  readonly onLink: () => void;
  readonly onSelectCustomer: (choice: CustomerChoice) => void;
  readonly working: boolean;
}) {
  const question = <div className="assistant-question"><span>Você</span><p>{turn.question}</p></div>;
  const reply = turn.reply;
  if (!reply) return <section className="assistant-turn">{question}</section>;
  const hasMetric = reply.facts.some((fact) => PRIMARY_METRICS.some((key) => typeof fact.values[key] === "number"));
  const answer = visibleAnswer(reply, hasMetric);
  const label = reply.source === "GROQ" ? "Assistente LoadX · Groq"
    : reply.source === "BACKEND" ? "Dados verificados · LoadX"
      : reply.source === "GUARDRAIL" ? "Proteção do LoadX · somente leitura"
        : "Resumo automático · IA indisponível";
  return <section className="assistant-turn">{question}
    <div className="assistant-response">
      <strong className="assistant-source">{label}</strong>
      {answer ? <p className="assistant-answer">{answer}</p> : null}
      {reply.facts.map((fact) => <Fact key={fact.clientKey} fact={fact} onLink={onLink} onSelectCustomer={onSelectCustomer} working={working} />)}
      <nav className="assistant-action-links" aria-label="Ações relacionadas">{reply.links.filter((link) => allowedLink(link.href)).map((link) =>
        <Link key={link.href} to={link.href} onClick={onLink}>{link.label}<Icon name="arrow-right" size={16} /></Link>
      )}</nav>
    </div>
  </section>;
}

export function AssistantConversation({ turns, onLink, onSelectCustomer, working }: {
  readonly turns: readonly Turn[];
  readonly onLink: () => void;
  readonly onSelectCustomer: (choice: CustomerChoice) => void;
  readonly working: boolean;
}) {
  const chat = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const container = chat.current;
    const lastTurn = container?.lastElementChild;
    if (!container || !(lastTurn instanceof HTMLElement)) return;
    // Exibir a pergunta e o início do resultado novo, não só o fim de uma
    // resposta longa. Nunca forçar scroll enquanto o usuário lê detalhes.
    container.scrollTop +=
      lastTurn.getBoundingClientRect().top - container.getBoundingClientRect().top;
  }, [turns.length]);
  return <div ref={chat} className="assistant-conversation" role="log" aria-label="Conversa com o LoadX" aria-live="polite">
    {turns.length === 0 ? <div className="assistant-welcome assistant-welcome-greeting"><div className="assistant-welcome-icon"><Icon name="message-circle" size={24} /></div><div className="assistant-welcome-copy"><span className="assistant-source">Loxi · Assistente LoadX</span><h3>Olá! Eu sou o Loxi 👋</h3><p>Posso conversar sobre sua operação, consultar registros autorizados e explicar os resultados do algoritmo nos planejamentos anteriores ou no mais recente.</p><p>Também posso orientar ações permitidas. Para ver ideias do que perguntar, é só escrever <strong>“Me dê sugestões”</strong>.</p></div></div> : null}
    {turns.map((turn) => <TurnRow key={turn.id} turn={turn} onLink={onLink} onSelectCustomer={onSelectCustomer} working={working} />)}
  </div>;
}
