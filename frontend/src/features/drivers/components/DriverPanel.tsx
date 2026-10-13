import { ImportAction } from "../../registration-imports/components/ImportAction";
import { useCallback, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { MAX_SEARCH_LENGTH, type ListParams } from "../../../services/pagination";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useEditTarget } from "../../../hooks/useEditTarget";
import { useRegistryList } from "../../../hooks/useRegistryList";
import { ArchiveFilter } from "../../../components/ArchiveFilter";
import { RecordLifecycleAction } from "../../../components/RecordLifecycleAction";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics } from "../../auth/permissions";
import { getDriver, listDrivers } from "../api/driversApi";
import type { DriverListItem, Driver } from "../types";
import { DocumentsPanel } from "./DocumentsPanel";
import { DriverForm } from "./DriverForm";
import { mapDriverErrorToMessage } from "./driversErrorMessages";
import { Icon } from "../../../components/Icon";

export function DriverPanel() {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const filteredLoad = useCallback((params: ListParams) => listDrivers({
    ...params,
    search,
  }), [search]);
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
  } = useRegistryList(filteredLoad);
  const edit = useEditTarget<Driver>(getDriver);
  const [documentsDriver, setDocumentsDriver] = useState<DriverListItem | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = canManageLogistics(user?.role);
  const isFormOpen = isCreating || edit.target !== null;

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
        {canManage ? <ImportAction entity="drivers" onImported={refetch} /> : null}
        <ArchiveFilter value={archiveStatus} onChange={setArchiveStatus} />
        <input
          type="search"
          aria-label="Buscar motorista por nome"
          placeholder="Buscar por nome"
          value={search}
          onChange={(event) => { goToPage(1); setSearch(event.target.value); }}
          maxLength={MAX_SEARCH_LENGTH}
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
          Exibindo {drivers.length} de {total} motoristas. Busca e filtros consideram toda a lista.
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

      {status === "success" && drivers.length === 0 ? (
        <p className="entity-state">
          {search.trim() === "" && archiveStatus === "active" && total === 0
            ? "Nenhum motorista cadastrado ainda."
            : "Nenhum motorista encontrado com esses filtros."}
        </p>
      ) : null}

      {drivers.length > 0 ? (
        <div className="entity-grid">
          {drivers.map((driver) => (
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
              <div className="contact-card-foot">
                <button type="button" className="btn-link" onClick={() => setDocumentsDriver(driver)}>
                  Documentos
                </button>
                {canManage ? (
                  <>
                    <RecordLifecycleAction resource="drivers" id={driver.id} active={driver.active} onChanged={refetch} />
                    <button
                      type="button"
                      className="btn-link"
                      disabled={edit.loadingId === driver.id}
                      onClick={() => void edit.open(driver.id)}
                    >
                      {edit.loadingId === driver.id ? "Abrindo…" : "Editar"}
                    </button>
                  </>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="motoristas" />
      ) : null}

      {documentsDriver ? <Modal title={`Documentos — ${documentsDriver.name}`} onClose={() => setDocumentsDriver(null)}><DocumentsPanel driver={documentsDriver} onChanged={refetch}/></Modal> : null}
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
