import { Fragment, useCallback, useEffect, useState, type FormEvent } from "react";

import { useAuth } from "../../auth/hooks/useAuth";
import { AlertBanner } from "../../../components/AlertBanner";
import { Icon } from "../../../components/Icon";
import { Pagination } from "../../../components/Pagination";
import { ApiError } from "../../../types/api";
import { listAuditEntries } from "../api/auditApi";
import {
  AUDIT_ENTITY_LABELS,
  AUDIT_EVENT_LABELS,
  describeAuditEntry,
} from "../components/auditLabels";
import {
  AUDIT_ENTITY_TYPES,
  AUDIT_EVENT_TYPES,
  type AuditEntityType,
  type AuditEntry,
  type AuditEventType,
  type AuditListParams,
} from "../types";
import { mapAuditErrorToMessage } from "./auditErrorMessages";
import "./AuditPage.css";

interface FilterDraft {
  entityType: AuditEntityType | "";
  entityId: string;
  actorId: string;
  eventType: AuditEventType | "";
  startAt: string;
  endAt: string;
}

const EMPTY_FILTERS: FilterDraft = {
  entityType: "",
  entityId: "",
  actorId: "",
  eventType: "",
  startAt: "",
  endAt: "",
};

function toIso(value: string): string | undefined {
  if (!value) return undefined;
  return new Date(value).toISOString();
}

function toAuditParams(filters: FilterDraft, page: number): AuditListParams {
  return {
    page,
    pageSize: 20,
    sortOrder: "desc",
    entityType: filters.entityType || undefined,
    entityId: filters.entityId.trim() || undefined,
    actorId: filters.actorId.trim() || undefined,
    eventType: filters.eventType || undefined,
    startAt: toIso(filters.startAt),
    endAt: toIso(filters.endAt),
  };
}

function eventTone(event: AuditEventType): "amber" | "blue" | "green" | "purple" | "red" {
  if (event === "STATUS_CHANGED" || event.includes("UPDATED") || event.includes("RENEWED")) return "amber";
  if (event.includes("ARCHIVED") || event.includes("REVOKED") || event.includes("REJECTED")) return "red";
  if (event.includes("REACTIVATED") || event.includes("COMPLETED") || event.includes("CLOSED")) return "green";
  if (event.includes("CREATED") || event.includes("REGISTERED")) return "blue";
  return "purple";
}

function actorInitials(name: string | null): string {
  if (!name) return "SX";
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toLocaleUpperCase("pt-BR");
}

export function AuditPage() {
  const { user } = useAuth();
  const canReadCompany = user?.role === "ADMIN";
  const [draft, setDraft] = useState<FilterDraft>(EMPTY_FILTERS);
  const [filters, setFilters] = useState<FilterDraft>(EMPTY_FILTERS);
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [state, setState] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    setErrorMessage(null);

    try {
      const result = await listAuditEntries(toAuditParams(filters, page));
      setEntries(result.items);
      setTotal(result.total);
      setTotalPages(result.totalPages);
      setState("success");
    } catch (error) {
      const apiError =
        error instanceof ApiError
          ? error
          : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapAuditErrorToMessage(apiError));
      setState("error");
    }
  }, [filters, page]);

  useEffect(() => {
    void load();
  }, [load]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setFilters(draft);
  }

  function clearFilters() {
    setDraft(EMPTY_FILTERS);
    setPage(1);
    setFilters(EMPTY_FILTERS);
  }

  return (
    <div className="entity-page audit-page">
      <header className="entity-header">
        <div className="audit-title-block">
          <span className="audit-title-icon"><Icon name="report" size={24} /></span>
          <div>
          <p className="eyebrow">CONTROLE</p>
          <h1>Auditoria</h1>
          <p className="entity-lede">
            Histórico somente leitura de mudanças operacionais e ações administrativas.
          </p>
          </div>
        </div>
      </header>

      <form className="audit-filters" onSubmit={applyFilters}>
        <div className="audit-filter-grid">
        <label>
          <span className="field-label">Entidade</span>
          <select
            value={draft.entityType}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                entityType: event.target.value as AuditEntityType | "",
              }))
            }
          >
            <option value="">Todas</option>
            {AUDIT_ENTITY_TYPES.filter((value) => canReadCompany || !["COMPANY_PROFILE", "ACCESS_PROFILE", "OUTBOX_EVENT"].includes(value)).map((value) => (
              <option key={value} value={value}>
                {AUDIT_ENTITY_LABELS[value]}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Evento</span>
          <select
            value={draft.eventType}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                eventType: event.target.value as AuditEventType | "",
              }))
            }
          >
            <option value="">Todos</option>
            {AUDIT_EVENT_TYPES.filter((value) => canReadCompany || (value !== "OUTBOX_REPROCESSED" && !value.startsWith("COMPANY_PROFILE_") && !value.startsWith("PROFILE_"))).map((value) => (
              <option key={value} value={value}>
                {AUDIT_EVENT_LABELS[value]}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">De</span>
          <input
            type="datetime-local"
            value={draft.startAt}
            onChange={(event) =>
              setDraft((current) => ({ ...current, startAt: event.target.value }))
            }
          />
        </label>

        <label>
          <span className="field-label">Até</span>
          <input
            type="datetime-local"
            value={draft.endAt}
            onChange={(event) =>
              setDraft((current) => ({ ...current, endAt: event.target.value }))
            }
          />
        </label>
        </div>

        <details className="audit-advanced-filters">
          <summary>Filtros avançados por identificador</summary>
          <div className="audit-filter-grid audit-filter-grid-advanced">
            <label>
              <span className="field-label">Identificador da entidade</span>
              <input type="text" placeholder="UUID completo" value={draft.entityId}
                onChange={(event) => setDraft((current) => ({ ...current, entityId: event.target.value }))} />
            </label>
            <label>
              <span className="field-label">Identificador do responsável</span>
              <input type="text" placeholder="UUID completo" value={draft.actorId}
                onChange={(event) => setDraft((current) => ({ ...current, actorId: event.target.value }))} />
            </label>
          </div>
        </details>

        <div className="audit-filter-actions">
          <button type="button" className="btn-secondary" onClick={clearFilters}>
            Limpar filtros
          </button>
          <button type="submit" className="btn-primary"><Icon name="search" size={17} />Aplicar filtros</button>
        </div>
      </form>

      <div className="audit-results-heading"><p><strong>{state === "success" ? total : "—"}</strong> evento(s) encontrado(s)</p><span>Filtros aplicados pelo servidor antes da paginação</span></div>

      {errorMessage ? <div className="audit-error"><AlertBanner>{errorMessage}</AlertBanner><button className="btn-secondary" type="button" onClick={() => void load()}>Tentar novamente</button></div> : null}

      {state === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando auditoria…</span>
        </p>
      ) : null}

      {state === "success" && entries.length === 0 ? (
        <div className="audit-empty"><Icon name="report" size={28} /><h2>Nenhum evento encontrado</h2><p>Ajuste os filtros para consultar outro período ou tipo de alteração.</p></div>
      ) : null}

      {entries.length > 0 && state !== "error" ? (
        <>
          <div className="audit-table-wrap">
            <table className="audit-table">
              <thead>
                <tr>
                  <th>Quando</th>
                  <th>Evento</th>
                  <th>Entidade</th>
                  <th>Responsável</th>
                  <th>Alteração</th>
                  <th><span className="sr-only">Ações</span></th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const shortId = entry.entityId.slice(0, 8).toLocaleUpperCase("pt-BR");
                  const isExpanded = expandedEntry === entry.id;
                  return <Fragment key={entry.id}>
                  <tr>
                    <td data-label="Quando">
                      <time dateTime={entry.createdAt}>
                        <strong>{new Date(entry.createdAt).toLocaleDateString("pt-BR")}</strong>
                        <span>{new Date(entry.createdAt).toLocaleTimeString("pt-BR")}</span>
                      </time>
                    </td>
                    <td data-label="Evento"><span className="audit-event-label" data-tone={eventTone(entry.eventType)}>{AUDIT_EVENT_LABELS[entry.eventType]}</span></td>
                    <td data-label="Entidade">
                      <span className="audit-entity-cell"><span className="audit-entity-icon"><Icon name="package" size={15} /></span><span><strong>{entry.entityName ?? AUDIT_ENTITY_LABELS[entry.entityType]}</strong><span className="audit-friendly-id">{AUDIT_ENTITY_LABELS[entry.entityType]} · {shortId}</span></span></span>
                    </td>
                    <td data-label="Responsável">
                      <span className="audit-actor"><span aria-hidden="true">{actorInitials(entry.actorName)}</span><strong>{entry.actorName ?? "Sistema"}</strong></span>
                    </td>
                    <td data-label="Alteração">{describeAuditEntry(entry)}</td>
                    <td data-label="Ações"><button className="audit-detail-toggle" type="button" aria-expanded={isExpanded}
                      aria-label={`${isExpanded ? "Ocultar" : "Ver"} detalhes do evento ${shortId}`}
                      onClick={() => setExpandedEntry(isExpanded ? null : entry.id)}><span aria-hidden="true">{isExpanded ? "−" : "›"}</span></button></td>
                  </tr>
                  {isExpanded ? <tr className="audit-detail-row"><td colSpan={6}>
                    <dl>
                      <div><dt>Identificador do evento</dt><dd><code>{entry.id}</code></dd></div>
                      <div><dt>Identificador da entidade</dt><dd><code>{entry.entityId}</code></dd></div>
                      <div><dt>Identificador do responsável</dt><dd><code>{entry.actorId ?? "Ação do sistema"}</code></dd></div>
                    </dl>
                  </td></tr> : null}
                  </Fragment>;
                })}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            onChange={setPage}
            label="auditoria"
          />
        </>
      ) : null}
    </div>
  );
}
