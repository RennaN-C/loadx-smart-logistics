import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useEditTarget } from "../../../hooks/useEditTarget";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { getDriver, listDrivers } from "../api/driversApi";
import type { Driver, DriverListItem } from "../types";
import { DriverForm } from "./DriverForm";
import { mapDriverErrorToMessage } from "./driversErrorMessages";

type StatusFilter = "all" | "active" | "inactive";

function matchesStatus(driver: DriverListItem, filter: StatusFilter): boolean {
  if (filter === "active") return driver.active;
  if (filter === "inactive") return !driver.active;
  return true;
}

export function DriverPanel() {
  const { user } = useAuth();
  const {
    status,
    items: drivers,
    error,
    refetch,
    page,
    total,
    totalPages,
    goToPage,
  } = useResourceList(listDrivers);
  const edit = useEditTarget<Driver>(getDriver);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || edit.target !== null;

  // Só nome: a listagem não traz documento nem CNH.
  const visibleDrivers = useMemo(() => {
    const term = search.trim().toLowerCase();

    return drivers.filter(
      (driver) =>
        (term === "" || driver.name.toLowerCase().includes(term)) && matchesStatus(driver, statusFilter),
    );
  }, [drivers, search, statusFilter]);

  function closeForm() {
    setIsCreating(false);
    edit.close();
  }

  async function handleSaved() {
    closeForm();
    await refetch();
  }

  return (
    <>
      <div className="entity-toolbar">
        <input
          type="search"
          aria-label="Buscar motorista por nome"
          placeholder="Buscar por nome"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select
          aria-label="Filtrar motoristas por status"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
        >
          <option value="all">Todos os status</option>
          <option value="active">Somente ativos</option>
          <option value="inactive">Somente inativos</option>
        </select>
        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            + Novo motorista
          </button>
        ) : null}
      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {drivers.length} de {total} motoristas. Busca e filtro atuam nesta página.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando motoristas…</span>
        </p>
      ) : null}

      {status === "error" && error ? <AlertBanner>{mapDriverErrorToMessage(error)}</AlertBanner> : null}
      {edit.error ? <AlertBanner>{mapDriverErrorToMessage(edit.error)}</AlertBanner> : null}

      {status === "success" && visibleDrivers.length === 0 ? (
        <p className="entity-state">
          {drivers.length === 0
            ? "Nenhum motorista cadastrado ainda."
            : "Nenhum motorista encontrado com esses filtros."}
        </p>
      ) : null}

      {visibleDrivers.length > 0 ? (
        <div className="entity-grid">
          {visibleDrivers.map((driver) => (
            <article key={driver.id} className="contact-card">
              <div className="contact-card-head">
                <p className="contact-card-name">{driver.name}</p>
                <StatusPill tone={driver.active ? "good" : "neutral"}>
                  {driver.active ? "Ativo" : "Inativo"}
                </StatusPill>
              </div>
              <dl className="contact-card-license">
                <div>
                  <dt>CATEGORIA</dt>
                  <dd>{driver.licenseCategory ?? "—"}</dd>
                </div>
              </dl>
              {canManage ? (
                <div className="contact-card-foot">
                  <button
                    type="button"
                    className="btn-link"
                    disabled={edit.loadingId === driver.id}
                    onClick={() => void edit.open(driver.id)}
                  >
                    {edit.loadingId === driver.id ? "Abrindo…" : "Editar"}
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="motoristas" />
      ) : null}

      {isFormOpen ? (
        <Modal
          title={edit.target ? "Editar motorista" : "Novo motorista"}
          subtitle="Condutor da viagem"
          onClose={closeForm}
        >
          <DriverForm driver={edit.target ?? undefined} onSaved={handleSaved} onCancel={closeForm} />
        </Modal>
      ) : null}
    </>
  );
}
