import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Icon } from "../../../components/Icon";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import { listTruckOperationalStatus } from "../api/trucksApi";
import { describeFleetStatus } from "../components/fleetStatusLabels";
import { mapTruckErrorToMessage } from "../components/trucksErrorMessages";
import type { TruckOperationalStatus } from "../types";
import "./FleetStatusPage.css";

type Filtro = "all" | "available" | "unavailable";

const FILTROS: ReadonlyArray<{ value: Filtro; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "available", label: "Disponíveis" },
  { value: "unavailable", label: "Indisponíveis" },
];

function atendeFiltro(truck: TruckOperationalStatus, filtro: Filtro): boolean {
  if (filtro === "available") return truck.available;
  if (filtro === "unavailable") return !truck.available;
  return true;
}

/**
 * Painel de situação da frota (OC73).
 *
 * Mostra o que `GET /trucks/operational-status` devolve e nada além disso.
 * `available` chega calculado pela OC67/OC68 — a tela não refaz a conta, só
 * agrupa e explica. Inventar estado aqui faria a frota parecer uma coisa na
 * tela e outra no planejamento.
 *
 * Os contadores valem para a PÁGINA carregada, não para a frota inteira: D12
 * mantém filtro e agregação server-side fora do contrato, e deixar isso
 * implícito faria alguém concluir que só existem três caminhões disponíveis.
 */
export function FleetStatusPage() {
  const { status, items, error, refetch, page, total, totalPages, goToPage } = useResourceList(
    listTruckOperationalStatus,
  );
  const [filtro, setFiltro] = useState<Filtro>("all");

  const visiveis = useMemo(
    () => items.filter((truck) => atendeFiltro(truck, filtro)),
    [items, filtro],
  );
  const disponiveis = useMemo(() => items.filter((truck) => truck.available).length, [items]);

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Situação da frota</h1>
          <p className="entity-lede">Quais caminhões podem receber carga agora.</p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => void refetch()}>
          <Icon name="gauge" size={16} />
          Atualizar
        </button>
      </header>

      <div className="entity-toolbar">
        <select
          aria-label="Filtrar por disponibilidade"
          value={filtro}
          onChange={(event) => setFiltro(event.target.value as Filtro)}
        >
          {FILTROS.map((opcao) => (
            <option key={opcao.value} value={opcao.value}>
              {opcao.label}
            </option>
          ))}
        </select>
      </div>

      {status === "success" && items.length > 0 ? (
        <p className="entity-summary">
          {disponiveis} de {items.length} disponíveis nesta página, de {total} caminhões. O filtro
          atua nesta página.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando a situação da frota…</span>
        </p>
      ) : null}

      {status === "error" && error ? (
        <>
          <AlertBanner>{mapTruckErrorToMessage(error)}</AlertBanner>
          <button type="button" className="btn-secondary" onClick={() => void refetch()}>
            Tentar novamente
          </button>
        </>
      ) : null}

      {status === "success" && visiveis.length === 0 ? (
        <p className="entity-state">
          {items.length === 0
            ? "Nenhum caminhão cadastrado ainda."
            : "Nenhum caminhão nesta situação, nesta página."}
        </p>
      ) : null}

      {visiveis.length > 0 ? (
        <ul className="fleet-grid">
          {visiveis.map((truck) => (
            <FleetStatusCard key={truck.id} truck={truck} />
          ))}
        </ul>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="caminhões" />
      ) : null}
    </div>
  );
}

function FleetStatusCard({ truck }: { readonly truck: TruckOperationalStatus }) {
  const { tone, label, reason } = describeFleetStatus(truck);

  return (
    <li className={truck.available ? "fleet-card" : "fleet-card fleet-card-off"}>
      <div className="fleet-card-head">
        <p className="fleet-card-plate">{truck.plate}</p>
        <StatusPill tone={tone}>{label}</StatusPill>
      </div>
      <p className="fleet-card-model">{truck.model}</p>
      {/* Sem motivo, nada ocupa a linha: um traço ou "—" pareceria informação. */}
      {reason === null ? null : <p className="fleet-card-reason">{reason}</p>}
    </li>
  );
}
