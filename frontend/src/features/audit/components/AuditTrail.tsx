import { useEffect, useState } from "react";

import { listAuditEntries } from "../api/auditApi";
import { AUDIT_EVENT_LABELS, describeAuditEntry } from "./auditLabels";
import type { AuditEntityType, AuditEntry } from "../types";

interface AuditTrailProps {
  readonly entityType: AuditEntityType;
  readonly entityId: string;
  readonly title?: string;
}

export function AuditTrail({
  entityType,
  entityId,
  title = "Histórico",
}: AuditTrailProps) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [state, setState] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");

    listAuditEntries({
      entityType,
      entityId,
      page: 1,
      pageSize: 8,
      sortOrder: "desc",
    })
      .then((result) => {
        if (!active) return;
        setEntries(result.items);
        setState("success");
      })
      .catch(() => {
        if (!active) return;
        // O componente contextual é complementar. A página principal continua
        // utilizável se a auditoria estiver temporariamente indisponível.
        setEntries([]);
        setState("error");
      });

    return () => {
      active = false;
    };
  }, [entityId, entityType]);

  return (
    <section className="audit-context" aria-labelledby={`audit-context-${entityId}`}>
      <div className="audit-context-header">
        <h2 id={`audit-context-${entityId}`}>{title}</h2>
        <span>Últimos eventos</span>
      </div>

      {state === "loading" ? <p className="entity-state">Carregando histórico…</p> : null}
      {state === "error" ? (
        <p className="entity-form-help">Histórico indisponível no momento.</p>
      ) : null}
      {state === "success" && entries.length === 0 ? (
        <p className="entity-form-help">Nenhum evento registrado para este item.</p>
      ) : null}

      {entries.length > 0 ? (
        <ol className="audit-context-list">
          {entries.map((entry) => (
            <li key={entry.id}>
              <div>
                <strong>{AUDIT_EVENT_LABELS[entry.eventType]}</strong>
                <p>{describeAuditEntry(entry)}</p>
              </div>
              <div className="audit-context-meta">
                <span>{entry.actorName ?? "Sistema"}</span>
                <time dateTime={entry.createdAt}>
                  {new Date(entry.createdAt).toLocaleString("pt-BR")}
                </time>
              </div>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
