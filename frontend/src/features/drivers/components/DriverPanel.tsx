import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { listDrivers } from "../api/driversApi";
import type { Driver } from "../types";
import { DriverForm } from "./DriverForm";
import { mapDriverErrorToMessage } from "./driversErrorMessages";

type StatusFilter = "all" | "active" | "inactive";

function matchesStatus(driver: Driver, filter: StatusFilter): boolean {
  if (filter === "active") return driver.active;
  if (filter === "inactive") return !driver.active;
  return true;
}

export function DriverPanel() {
  const { user } = useAuth();
  const { status, items: drivers, error, refetch } = useResourceList(listDrivers);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [editingDriver, setEditingDriver] = useState<Driver | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || editingDriver !== null;

  const visibleDrivers = useMemo(() => {
    const term = search.trim().toLowerCase();

    return drivers.filter((driver) => {
      const matchesTerm =
        term === "" ||
        driver.name.toLowerCase().includes(term) ||
        driver.document.toLowerCase().includes(term) ||
        driver.licenseNumber.toLowerCase().includes(term);

      return matchesTerm && matchesStatus(driver, statusFilter);
    });
  }, [drivers, search, statusFilter]);

  function closeForm() {
    setIsCreating(false);
    setEditingDriver(null);
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
          aria-label="Buscar motorista por nome, documento ou CNH"
          placeholder="Buscar por nome, documento ou CNH"
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

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando motoristas…</span>
        </p>
      ) : null}

      {status === "error" && error ? <AlertBanner>{mapDriverErrorToMessage(error)}</AlertBanner> : null}

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
              <p className="contact-card-line">{driver.document}</p>
              <p className="contact-card-line">{driver.phone}</p>
              <dl className="contact-card-license">
                <div>
                  <dt>CNH</dt>
                  <dd>{driver.licenseNumber}</dd>
                </div>
                <div>
                  <dt>CATEGORIA</dt>
                  <dd>{driver.licenseCategory ?? "—"}</dd>
                </div>
              </dl>
              {canManage ? (
                <div className="contact-card-foot">
                  <button type="button" className="btn-link" onClick={() => setEditingDriver(driver)}>
                    Editar
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {isFormOpen ? (
        <Modal
          title={editingDriver ? "Editar motorista" : "Novo motorista"}
          subtitle="Condutor da viagem"
          onClose={closeForm}
        >
          <DriverForm driver={editingDriver ?? undefined} onSaved={handleSaved} onCancel={closeForm} />
        </Modal>
      ) : null}
    </>
  );
}
