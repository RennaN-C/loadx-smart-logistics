import { Link } from "react-router-dom";
import { PLAN_STATUS_LABELS, REJECTION_LABELS } from "../load-planning/components/loadPlanLabels";
import type { AssistantFact, AssistantReply } from "./assistantApi";

const LABELS: Record<string, string> = {
  ...PLAN_STATUS_LABELS, ...REJECTION_LABELS,
  DRAFT: "Rascunho", READY: "Pronto para coleta", PLANNED: "Planejado", IN_TRANSIT: "Em trânsito", DELIVERED: "Entregue", CANCELED: "Cancelado",
  PROPOSED: "Proposta", PARTIALLY_APPROVED: "Parcialmente aprovada", INCOMPLETE: "Incompleta",
  insufficient_data: "Dados insuficientes", ambiguous_customer: "Mais de um cliente encontrado", customer_not_found: "Cliente não encontrado",
};
const FACT_LABELS: Record<string, string> = {
  "fully_delivered_orders": "Pedidos totalmente entregues",
  "dispatched_orders": "Pedidos expedidos distintos",
  "completed_delivery_legs": "Pernas de entrega concluídas",
  "top_customer_name": "Cliente com mais pedidos entregues",
  "top_customer_delivered_orders": "Pedidos entregues do cliente líder",
  "trips_started": "Viagens iniciadas",
  "trips_finished": "Viagens concluídas",
  "distinct_trucks_used": "Caminhões utilizados",
  "plans_with_started_trip": "Planos com viagem iniciada",
  "average_plan_occupancy_percent": "Ocupação média por plano (%)",
  "planned_loaded_volumes": "Volumes carregados nos planos",
  "planned_rejected_volumes": "Volumes rejeitados nos planos",
  "planned_loaded_weight_kg": "Peso planejado carregado (kg)",
  "currently_canceled_distributions_created_in_period": "Distribuições canceladas criadas no período",
  "page": "Página",
  "total_pages": "Total de páginas",
  "page_records": "Registros nesta página",
  "page_vehicle_count": "Veículos nesta página",
  "page_active_count": "Ativos nesta página",
  "page_archived_count": "Arquivados nesta página",
  "page_unavailable_count": "Indisponíveis nesta página",
  "unavailable_vehicles": "Veículos indisponíveis",
  "result": "Resultado",
  "bounded_matches": "Correspondências encontradas (limitadas)",
  "required_data": "Dados necessários",
  "company": "Empresa",
  "status": "Situação",
  "loaded_volumes": "Volumes carregados",
  "rejected_volumes": "Volumes rejeitados",
  "occupancy_percent": "Ocupação (%)",
  "weight_kg": "Peso (kg)",
  "truck_capacity_weight_kg": "Capacidade de peso (kg)",
  "internal_width_cm": "Largura interna (cm)",
  "internal_height_cm": "Altura interna (cm)",
  "internal_length_cm": "Comprimento interno (cm)",
  "truck_count": "Caminhões",
  "volume_count": "Volumes"
};
function readable(value: string): string { return LABELS[value] ?? FACT_LABELS[value] ?? value.replaceAll("_", " "); }

export interface Turn { question: string; reply?: AssistantReply }
function formatValue(value: string | number | null): string {
  if (value === null) return "Sem dados";
  return typeof value === "number" ? value.toLocaleString("pt-BR") : readable(value);
}
function allowedLink(href: string): boolean {
  return ["/trucks?tab=availability", "/orders", "/deliveries", "/reports", "/planning"].includes(href) || /^\/planning\/(?:distributions\/)?[0-9a-f-]{36}$/i.test(href);
}
function Fact({ fact, onLink }: { readonly fact: AssistantFact; readonly onLink: () => void }) {
  return <details className="assistant-fact" open><summary>{fact.name}</summary><p>{fact.criteria}</p>
    {fact.period_start && fact.period_end ? <p>Período: {new Date(fact.period_start).toLocaleString("pt-BR", { timeZone: "UTC" })} até {new Date(fact.period_end).toLocaleString("pt-BR", { timeZone: "UTC" })} (fim exclusivo, UTC).</p> : null}
    <nav aria-label="Registros da consulta">{fact.links?.filter((link) => allowedLink(link.href)).map((link) => <Link key={link.href} to={link.href} onClick={onLink}>{link.label}</Link>)}</nav>
    <dl>{Object.entries(fact.values).map(([key, value]) => <div key={key}><dt>{readable(key)}</dt><dd>{formatValue(value)}</dd></div>)}</dl>
  </details>;
}
function TurnRow({ turn, onLink }: { readonly turn: Turn; readonly onLink: () => void }) {
  const question = <p className="assistant-question"><strong>Você</strong>{turn.question}</p>;
  const reply = turn.reply;
  if (!reply) return <section className="assistant-turn">{question}</section>;
  return <section className="assistant-turn">{question}
    <strong className="assistant-source">{reply.source === "GROQ" ? "Assistente LoadX · IA real (Groq)" : "Resumo automático · IA indisponível"}</strong><p className="assistant-answer">{reply.answer}</p>
    {reply.facts.map((fact, index) => <Fact key={index} fact={fact} onLink={onLink} />)}
    <nav aria-label="Recursos relacionados">{reply.links.filter((link) => allowedLink(link.href)).map((link) => <Link key={link.href} to={link.href} onClick={onLink}>{link.label}</Link>)}</nav>
  </section>;
}
export function AssistantConversation({ turns, onLink }: { readonly turns: readonly Turn[]; readonly onLink: () => void }) {
  return <div className="assistant-conversation" role="log" aria-label="Conversa com o LoadX" aria-live="polite">
    {turns.length === 0 ? <div className="assistant-welcome"><h3>Como posso ajudar na operação?</h3><p>Entenda uma carga, consulte indicadores ou encontre o próximo passo permitido.</p></div> : null}
    {turns.map((turn, index) => <TurnRow key={index} turn={turn} onLink={onLink} />)}
  </div>;
}
