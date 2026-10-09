import { ImportAction } from "../../registration-imports/components/ImportAction";
import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics } from "../../auth/permissions";
import { TruckCard } from "../components/TruckCard";
import { DocumentsPanel } from "../components/DocumentsPanel";
import { MaintenancePanel } from "../components/MaintenancePanel";
import { TruckForm } from "../components/TruckForm";
import { mapTruckErrorToMessage } from "../components/trucksErrorMessages";
import { Pagination } from "../../../components/Pagination";
import { useRegistryList } from "../../../hooks/useRegistryList";
import { ArchiveFilter } from "../../../components/ArchiveFilter";

import { listTrucks } from "../api/trucksApi";
import type { Truck } from "../types";
import "./TruckListPage.css";
import { Icon } from "../../../components/Icon";

export function TruckListPage() {
  const { user } = useAuth();
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
  } = useRegistryList(listTrucks);
  const [documentsTruck, setDocumentsTruck] = useState<Truck | null>(null);
  const [maintenanceTruck, setMaintenanceTruck] = useState<Truck | null>(null);
  const [search, setSearch] = useState("");
  const [editingTruck, setEditingTruck] = useState<Truck | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = canManageLogistics(user?.role);
  const isFormOpen = isCreating || editingTruck !== null;

  // A busca textual permanece local; o arquivamento é filtrado pelo servidor (OC105).
  const visibleTrucks = useMemo(() => {
    const term = search.trim().toLowerCase();

    return trucks.filter((truck) => {
      const matchesTerm =
        term === "" ||
        truck.plate.toLowerCase().includes(term) ||
        truck.model.toLowerCase().includes(term);

      return matchesTerm;
    });
  }, [trucks, search]);

  function closeForm() {
    setIsCreating(false);
    setEditingTruck(null);
  }

  async function handleSaved() {
    closeForm();
    await refetch();
  }

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Caminhões</h1>
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
        {canManage ? <ImportAction entity="trucks" onImported={refetch} /> : null}
        <ArchiveFilter value={archiveStatus} onChange={setArchiveStatus} />
        <input
          type="search"
          aria-label="Buscar por placa ou modelo"
          placeholder="Buscar por placa ou modelo"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {trucks.length} de {total} caminhões. A busca atua nesta página; arquivamento filtra toda a lista.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando caminhões…</span>
        </p>
      ) : null}

      {status === "error" && error ? (
        <AlertBanner>{mapTruckErrorToMessage(error)}</AlertBanner>
      ) : null}

      {status === "success" && visibleTrucks.length === 0 ? (
        <p className="entity-state">
          {trucks.length === 0
            ? "Nenhum caminhão cadastrado ainda."
            : "Nenhum caminhão encontrado com esses filtros."}
        </p>
      ) : null}

      {visibleTrucks.length > 0 ? (
        <div className="entity-grid">
          {visibleTrucks.map((truck) => (
            <TruckCard key={truck.id} truck={truck} canManage={canManage} onEdit={setEditingTruck} onChanged={refetch} onMaintenance={setMaintenanceTruck} onDocuments={setDocumentsTruck} />
          ))}
        </div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="caminhões" />
      ) : null}

      {documentsTruck ? <Modal title={`Documentos — ${documentsTruck.plate}`} onClose={() => setDocumentsTruck(null)}>
        <DocumentsPanel truck={documentsTruck} onChanged={refetch} />
      </Modal> : null}
      {maintenanceTruck ? <Modal title={`Manutenções — ${maintenanceTruck.plate}`} onClose={() => setMaintenanceTruck(null)}>
        <MaintenancePanel truck={maintenanceTruck} onChanged={refetch} />
      </Modal> : null}

      {isFormOpen ? (
        <Modal
          title={editingTruck ? "Editar caminhão" : "Novo caminhão"}
          subtitle="Compartimento de carga"
          onClose={closeForm}
        >
          <TruckForm truck={editingTruck ?? undefined} onSaved={handleSaved} onCancel={closeForm} />
        </Modal>
      ) : null}
    </div>
  );
}
