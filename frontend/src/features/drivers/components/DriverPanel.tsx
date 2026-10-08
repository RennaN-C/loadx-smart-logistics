import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useEditTarget } from "../../../hooks/useEditTarget";
import { useRegistryList } from "../../../hooks/useRegistryList";
import { ArchiveFilter } from "../../../components/ArchiveFilter";
import { RecordLifecycleAction } from "../../../components/RecordLifecycleAction";
import { useAuth } from "../../auth/hooks/useAuth";
import { getDriver, listDrivers } from "../api/driversApi";
import type { Driver } from "../types";
import { DriverForm } from "./DriverForm";
import { mapDriverErrorToMessage } from "./driversErrorMessages";
import { Icon } from "../../../components/Icon";

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
    archiveStatus,
    setArchiveStatus,
  } = useRegistryList(listDrivers);
  const edit = useEditTarget<Driver>(getDriver);
  const [search, setSearch] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || edit.target !== null;

  // Só nome: a listagem não traz documento nem CNH.
  const visibleDrivers = useMemo(() => {
    const term = search.trim().toLowerCase();

    return drivers.filter(
      (driver) =>
        (term === "" || driver.name.toLowerCase().includes(term)),
    );
  }, [drivers, search]);

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
        <ArchiveFilter value={archiveStatus} onChange={setArchiveStatus} />
        <input
          type="search"
          aria-label="Buscar motorista por nome"
          placeholder="Buscar por nome"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            <Icon name="plus" size={16} />
            Novo motorista
          </button>
        ) : null}
      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {drivers.length} de {total} motoristas. A busca atua nesta página; arquivamento filtra toda a lista.
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
                  {driver.active ? "Ativo" : "Arquivado"}
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
                  <RecordLifecycleAction resource="drivers" id={driver.id} active={driver.active} onChanged={refetch} />
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
