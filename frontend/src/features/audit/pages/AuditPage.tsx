import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
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

export function AuditPage() {
  const [draft, setDraft] = useState<FilterDraft>(EMPTY_FILTERS);
  const [filters, setFilters] = useState<FilterDraft>(EMPTY_FILTERS);
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [state, setState] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
        <div>
          <h1>Auditoria</h1>
          <p className="entity-lede">
            Histórico somente leitura de mudanças operacionais e ações administrativas.
          </p>
        </div>
      </header>

      <form className="audit-filters" onSubmit={applyFilters}>
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
            {AUDIT_ENTITY_TYPES.map((value) => (
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
            {AUDIT_EVENT_TYPES.map((value) => (
              <option key={value} value={value}>
                {AUDIT_EVENT_LABELS[value]}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">ID da entidade</span>
          <input
            type="text"
            placeholder="UUID"
            value={draft.entityId}
            onChange={(event) =>
              setDraft((current) => ({ ...current, entityId: event.target.value }))
            }
          />
        </label>

        <label>
          <span className="field-label">ID do responsável</span>
          <input
            type="text"
            placeholder="UUID"
            value={draft.actorId}
            onChange={(event) =>
              setDraft((current) => ({ ...current, actorId: event.target.value }))
            }
          />
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

        <div className="audit-filter-actions">
          <button type="submit" className="btn-primary">
            Aplicar filtros
          </button>
          <button type="button" className="btn-secondary" onClick={clearFilters}>
            Limpar
          </button>
        </div>
      </form>

      <p className="entity-summary">
        Os filtros são aplicados pelo servidor antes da paginação.
      </p>

      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      {state === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando auditoria…</span>
        </p>
      ) : null}

      {state === "success" && entries.length === 0 ? (
        <p className="entity-state">Nenhum evento encontrado com esses filtros.</p>
      ) : null}

      {entries.length > 0 && state !== "error" ? (
        <>
          <p className="audit-count">{total} evento(s) encontrado(s).</p>
          <div className="audit-table-wrap">
            <table className="audit-table">
              <thead>
                <tr>
                  <th>Quando</th>
                  <th>Evento</th>
                  <th>Entidade</th>
                  <th>Responsável</th>
                  <th>Alteração</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>
                      <time dateTime={entry.createdAt}>
                        {new Date(entry.createdAt).toLocaleString("pt-BR")}
                      </time>
                    </td>
                    <td>{AUDIT_EVENT_LABELS[entry.eventType]}</td>
                    <td>
                      <strong>{AUDIT_ENTITY_LABELS[entry.entityType]}</strong>
                      <code>{entry.entityId}</code>
                    </td>
                    <td>
                      <strong>{entry.actorName ?? "Sistema"}</strong>
                      {entry.actorId ? <code>{entry.actorId}</code> : null}
                    </td>
                    <td>{describeAuditEntry(entry)}</td>
                  </tr>
                ))}
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
