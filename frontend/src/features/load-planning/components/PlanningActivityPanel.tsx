import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Icon } from "../../../components/Icon";
import { listAuditEntries } from "../../audit/api/auditApi";
import { AUDIT_EVENT_LABELS, describeAuditEntry } from "../../audit/components/auditLabels";
import type { AuditEntry } from "../../audit/types";

const timeFormatter = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

export function PlanningActivityPanel() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setFailed(false);
    Promise.all(["LOAD_PLAN", "LOAD_DISTRIBUTION", "LOAD_DISTRIBUTION_PART", "ORDER"].map((entityType) =>
      Promise.resolve(listAuditEntries({ page: 1, pageSize: 3, sortOrder: "desc", entityType: entityType as "LOAD_PLAN" | "LOAD_DISTRIBUTION" | "LOAD_DISTRIBUTION_PART" | "ORDER" }))))
      .then((results) => {
        if (active) setEntries(results.flatMap((result) => result.items).sort((first, second) => second.createdAt.localeCompare(first.createdAt)).slice(0, 6));
      })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [attempt]);

  return <aside className="planning-activity" aria-labelledby="planning-activity-title">
    <header><div><Icon name="chart" size={18} /><h2 id="planning-activity-title">Atividade e auditoria</h2></div><Link to="/audit">Ver todas <Icon name="arrow-right" size={13} /></Link></header>
    {entries === null && !failed ? <p className="planning-activity-state"><span className="spinner" />Carregando atividade…</p> : null}
    {failed ? <div className="planning-activity-state"><p>Não foi possível consultar a atividade.</p><button type="button" className="btn-link" onClick={() => setAttempt((value) => value + 1)}>Tentar novamente</button></div> : null}
    {entries?.length === 0 ? <p className="planning-activity-state">Nenhuma alteração de plano registrada.</p> : null}
    {entries && entries.length > 0 ? <ol>{entries.map((entry) => <li key={entry.id}><span className="planning-activity-dot" /><div className="planning-activity-meta"><time dateTime={entry.createdAt}>{timeFormatter.format(new Date(entry.createdAt))}</time><span>{entry.actorName ?? "Sistema"}</span></div><strong>{AUDIT_EVENT_LABELS[entry.eventType]}</strong><p>{entry.entityName ?? `Plano ${entry.entityId.slice(0, 8).toLocaleUpperCase("pt-BR")}`}</p><small>{describeAuditEntry(entry)}</small></li>)}</ol> : null}
  </aside>;
}
