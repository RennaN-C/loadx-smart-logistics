import { useUrlSearch } from "../../../hooks/useUrlSearch";
import { ImportAction } from "../../registration-imports/components/ImportAction";
import { useCallback, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics, hasPermission } from "../../auth/permissions";
import { TruckDialogs } from "../components/TruckDialogs";
import { TruckCard } from "../components/TruckCard";
import { mapTruckErrorToMessage } from "../components/trucksErrorMessages";
import { MAX_SEARCH_LENGTH, type ListParams } from "../../../services/pagination";
import { Pagination } from "../../../components/Pagination";
import { useRegistryList } from "../../../hooks/useRegistryList";
import { ArchiveFilter } from "../../../components/ArchiveFilter";

import { listTrucks } from "../api/trucksApi";
import type { Truck } from "../types";
import "./TruckListPage.css";
import { Icon } from "../../../components/Icon";

export function TruckListPage({ embedded = false, active = true }: { readonly embedded?: boolean; readonly active?: boolean }) {
  const { user } = useAuth();
  const [search, setSearch] = useUrlSearch();
  const filteredLoad = useCallback((params: ListParams) => listTrucks({
    ...params,
    search,
  }), [search]);
  const {
    status,
    items: trucks,
    error,
    refetch,
    page,
    total,
    totalPages,
    goToPage,
    archiveStatus,
    setArchiveStatus,
  } = useRegistryList(filteredLoad);
  const [documentsTruck, setDocumentsTruck] = useState<Truck | null>(null);
  const [maintenanceTruck, setMaintenanceTruck] = useState<Truck | null>(null);
  const [editingTruck, setEditingTruck] = useState<Truck | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = canManageLogistics(user, "trucks");

  function closeForm() {
    setIsCreating(false);
    setEditingTruck(null);
  }

  async function handleSaved() {
    closeForm();
    await refetch();
  }

  return (
    <div className={embedded ? "truck-section" : "entity-page"}>
      <header className="entity-header">
        <div>
          {embedded ? <h2>Veículos</h2> : <h1>Caminhões</h1>}
          <p className="entity-lede">Baús cadastrados para planejamento de carga.</p>
        </div>
        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            <Icon name="plus" size={16} />
            Novo caminhão
          </button>
        ) : null}
      </header>

      <div className="entity-toolbar">
        <ImportAction enabled={hasPermission(user, "loadx.imports.manage")} entity="trucks" onImported={refetch} />
        <ArchiveFilter value={archiveStatus} onChange={setArchiveStatus} />
        <input
          type="search"
          aria-label="Buscar por placa ou modelo"
          placeholder="Buscar por placa ou modelo"
          value={search}
          onChange={(event) => { goToPage(1); setSearch(event.target.value); }}
          maxLength={MAX_SEARCH_LENGTH}
        />

      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {trucks.length} de {total} caminhões. Busca e filtros consideram toda a lista.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando caminhões…</span>
        </p>
      ) : null}

      {status === "error" && error ? (
        <><AlertBanner>{mapTruckErrorToMessage(error)}</AlertBanner><button type="button" className="btn-secondary" onClick={() => void refetch()}>Tentar novamente</button></>
      ) : null}

      {status === "success" && trucks.length === 0 ? (
        <p className="entity-state">
          {search.trim() === "" && archiveStatus === "active" && total === 0
            ? "Nenhum caminhão cadastrado ainda."
            : "Nenhum caminhão encontrado com esses filtros."}
        </p>
      ) : null}

      {trucks.length > 0 ? (
        <div className="entity-grid">
          {trucks.map((truck) => (
            <TruckCard key={truck.id} truck={truck} canManage={canManage} onEdit={setEditingTruck} onChanged={refetch} onMaintenance={setMaintenanceTruck} onDocuments={setDocumentsTruck} />
          ))}
        </div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="caminhões" />
      ) : null}

      <TruckDialogs active={active} documentsTruck={documentsTruck} maintenanceTruck={maintenanceTruck} editingTruck={editingTruck} isCreating={isCreating} onCloseDocuments={() => setDocumentsTruck(null)} onCloseMaintenance={() => setMaintenanceTruck(null)} onCloseForm={closeForm} onChanged={refetch} onSaved={handleSaved} />

    </div>
  );
}
