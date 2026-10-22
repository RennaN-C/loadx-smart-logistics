import { useEffect, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { getTripTimeline, type TimelinePage, type TimelineEvent } from "../api/timelineApi";
import "./TripTimeline.css";

const date = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

const eventLabels: Readonly<Record<string, string>> = {
  STATUS_CHANGED: "Mudança de situação",
  CUSTOMER_ABSENT: "Cliente ausente",
  REFUSED: "Entrega recusada",
  DAMAGED: "Avaria",
  OPERATIONAL_FAILURE: "Falha operacional",
  RESCHEDULED: "Reagendamento registrado",
  RESUMED: "Viagem ou tentativa retomada",
  INTERRUPTED: "Viagem interrompida",
  TRIP_CANCELED: "Viagem cancelada",
};

function description(event: TimelineEvent): string {
  const kind = eventLabels[event.kind] ?? event.kind.replaceAll("_", " ");
  return event.status_after ? `${kind}: ${event.status_before ?? "—"} → ${event.status_after}` : kind;
}

/** Projecao somente leitura do ledger, sem expor motivos pessoais ou midias. */
export function TripTimeline({ tripId }: { readonly tripId: string }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<TimelinePage | null>(null);
  const [state, setState] = useState<"loading" | "error" | "ready">("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setState("loading");
    getTripTimeline(tripId, page).then(result => {
      if (active) { setData(result); setState("ready"); }
    }).catch(() => { if (active) { setData(null); setState("error"); } });
    return () => { active = false; };
  }, [tripId, page, attempt]);

  useEffect(() => { setPage(1); }, [tripId]);

  return <section className="trip-timeline" aria-label="Linha do tempo da viagem">
    <div className="trip-timeline-heading">
      <div><h2>Linha do tempo operacional</h2><p>Eventos auditáveis da viagem e de suas entregas, em ordem cronológica.</p></div>
      <button className="btn-secondary" type="button" onClick={() => setAttempt(n => n + 1)}>Atualizar</button>
    </div>
    {state === "loading" && <p role="status">Consultando eventos…</p>}
    {state === "error" && <AlertBanner>Não foi possível consultar a linha do tempo. Atualize para tentar novamente.</AlertBanner>}
    {state === "ready" && data && data.items.length === 0 && <p className="entity-state">Nenhum evento encontrado nesta página.</p>}
    {state === "ready" && data && <>
      <p className="entity-form-help">{data.total} evento(s) persistidos. Não são mostradas descrições livres nem evidências privadas.</p>
      <ol>{data.items.map(event => <li key={`${event.source}:${event.id}`}>
        <time dateTime={event.occurred_at}>{date.format(new Date(event.occurred_at))}</time>
        <span>{description(event)}</span>
      </li>)}</ol>
      <nav className="trip-timeline-pagination" aria-label="Páginas do histórico">
        <button className="btn-secondary" type="button" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</button>
        <span>Página {page} de {Math.max(1, Math.ceil(data.total / data.page_size))}</span>
        <button className="btn-secondary" type="button" disabled={page * data.page_size >= data.total} onClick={() => setPage(p => p + 1)}>Próxima</button>
      </nav>
    </>}
  </section>;
}
