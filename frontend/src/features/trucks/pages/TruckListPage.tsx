import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { useAuth } from "../../auth/hooks/useAuth";
import { TruckCard } from "../components/TruckCard";
import { TruckForm } from "../components/TruckForm";
import { mapTruckErrorToMessage } from "../components/trucksErrorMessages";
import { useTrucks } from "../hooks/useTrucks";
import type { Truck } from "../types";
import "./TruckListPage.css";

type StatusFilter = "all" | "active" | "inactive";

function matchesStatus(truck: Truck, filter: StatusFilter): boolean {
  if (filter === "active") return truck.active;
  if (filter === "inactive") return !truck.active;
  return true;
}

export function TruckListPage() {
  const { user } = useAuth();
  const { status, trucks, error, refetch } = useTrucks();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [editingTruck, setEditingTruck] = useState<Truck | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || editingTruck !== null;

  // O backend ainda não aceita busca nem filtro por query param: ambos são client-side.
  const visibleTrucks = useMemo(() => {
    const term = search.trim().toLowerCase();

    return trucks.filter((truck) => {
      const matchesTerm =
        term === "" ||
        truck.plate.toLowerCase().includes(term) ||
        truck.model.toLowerCase().includes(term);

      return matchesTerm && matchesStatus(truck, statusFilter);
    });
  }, [trucks, search, statusFilter]);

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
            + Novo caminhão
          </button>
        ) : null}
      </header>

      <div className="entity-toolbar">
        <input
          type="search"
          aria-label="Buscar por placa ou modelo"
          placeholder="Buscar por placa ou modelo"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select
          aria-label="Filtrar por status"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
        >
          <option value="all">Todos os status</option>
          <option value="active">Somente ativos</option>
          <option value="inactive">Somente inativos</option>
        </select>
      </div>

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
            <TruckCard key={truck.id} truck={truck} canManage={canManage} onEdit={setEditingTruck} />
          ))}
        </div>
      ) : null}

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
