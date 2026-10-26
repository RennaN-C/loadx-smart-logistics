import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../../components/Icon";
import { StatusPill } from "../../../components/StatusPill";
import { listAuditEntries } from "../../audit/api/auditApi";
import { AUDIT_ENTITY_LABELS, AUDIT_EVENT_LABELS, auditStatusLabel } from "../../audit/components/auditLabels";
import type { AuditEntry, AuditEntityType } from "../../audit/types";

const PLANNING_ENTITIES: readonly AuditEntityType[] = ["LOAD_PLAN", "LOAD_DISTRIBUTION", "LOAD_DISTRIBUTION_PART"];

export function PlanningActivity() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setEntries(null); setFailed(false);
    // The latest eight from each stream contain the latest eight of their union.
    Promise.all(PLANNING_ENTITIES.map((entityType) => listAuditEntries({ entityType, page: 1, pageSize: 8, sortOrder: "desc" })))
      .then((pages) => {
        if (active) setEntries(pages.flatMap((page) => page.items).sort((a, b) => b.createdAt.localeCompare(a.createdAt) || b.id.localeCompare(a.id)).slice(0, 8));
      }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [attempt]);
  return <aside className="planning-activity" aria-labelledby="planning-activity-title">
    <header><h2 id="planning-activity-title"><Icon name="chart" size={18} />Atividade e auditoria</h2><Link to="/audit">Ver todas →</Link></header>
    {failed ? <div role="alert"><p>Não foi possível consultar a atividade.</p><button className="btn-secondary" type="button" onClick={() => setAttempt((value) => value + 1)}>Recarregar atividade</button></div>
      : entries === null ? <p role="status">Carregando atividade…</p>
        : entries.length === 0 ? <p>Nenhuma atividade de planejamento registrada.</p>
          : <ol>{entries.map((entry) => <li key={entry.id}>
            <div className="planning-activity-meta"><time dateTime={entry.createdAt}>{new Date(entry.createdAt).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</time><span>{entry.actorName ?? "Sistema"}</span></div>
            <strong>{AUDIT_EVENT_LABELS[entry.eventType]}</strong>
            <p>{AUDIT_ENTITY_LABELS[entry.entityType]} · {entry.entityName ?? entry.entityId.slice(0, 8)}</p>
            <small title={entry.entityId}>ID: {entry.entityId.slice(0, 8)}</small>
            {entry.newStatus ? <div className="planning-activity-transition"><span>{auditStatusLabel(entry.oldStatus)}</span><span aria-hidden="true">→</span><StatusPill tone={entry.newStatus === "APPROVED" ? "good" : "warn"}>{auditStatusLabel(entry.newStatus)}</StatusPill></div> : null}
          </li>)}</ol>}
  </aside>;
}
