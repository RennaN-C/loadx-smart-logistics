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
 * OC95: contadores e filtro de disponibilidade permanecem por página. A
 * fronteira atual calcula por ID após paginar; filtragem global depende de
 * evolução arquitetural sem duplicar regras operacionais. O aviso é explícito.
 */
export function FleetStatusPage({ embedded = false }: { readonly embedded?: boolean }) {
  const { status, items, error, refetch, page, total, totalPages, goToPage } = useResourceList(
    listTruckOperationalStatus,
  );
  const [filtro, setFiltro] = useState<Filtro>("all");

  const visiveis = useMemo(
    () => items.filter((truck) => atendeFiltro(truck, filtro)),
    [items, filtro],
  );
  const disponiveis = useMemo(() => items.filter((truck) => truck.available).length, [items]);
  const operando = useMemo(() => items.filter((truck) => truck.hasOperationConflict).length, [items]);
  const manutencao = useMemo(() => items.filter((truck) => truck.hasMaintenanceConflict).length, [items]);
  const documentos = useMemo(() => items.filter((truck) => truck.hasDocumentConflict).length, [items]);

  return (
    <div className={embedded ? "truck-section" : "entity-page"}>
      <header className="entity-header">
        <div>
          {embedded ? <h2>Disponibilidade</h2> : <h1>Situação da frota</h1>}
          <p className="entity-lede">Quais caminhões podem receber carga agora.</p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => void refetch()}>
          <Icon name="gauge" size={16} />
          Atualizar
        </button>
      </header>

      {status === "success" && items.length > 0 ? <div className="fleet-metrics" aria-label="Resumo da página da frota">
        <FleetMetric icon="truck" label="Veículos cadastrados" value={total} detail="Total filtrado" />
        <FleetMetric icon="gauge" label="Disponíveis" value={disponiveis} detail="Nesta página" />
        <FleetMetric icon="planning" label="Em operação" value={operando} detail="Nesta página" />
        <FleetMetric icon="settings" label="Em manutenção" value={manutencao} detail="Nesta página" />
        <FleetMetric icon="report" label="Pendência documental" value={documentos} detail="Nesta página" />
      </div> : null}

      <div className="entity-toolbar fleet-filterbar">
        <label className="registry-filter-field"><span>Disponibilidade</span><select
          aria-label="Filtrar por disponibilidade"
          value={filtro}
          onChange={(event) => setFiltro(event.target.value as Filtro)}
        >
          {FILTROS.map((opcao) => (
            <option key={opcao.value} value={opcao.value}>
              {opcao.label}
            </option>
          ))}
        </select></label>
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
        <div className="registry-table-wrap"><table className="registry-table fleet-table"><caption className="sr-only">Disponibilidade operacional dos caminhões</caption><thead><tr><th scope="col">Placa</th><th scope="col">Modelo</th><th scope="col">Disponibilidade</th><th scope="col">Motivo</th></tr></thead><tbody>{visiveis.map((truck) => <FleetStatusCard key={truck.id} truck={truck} />)}</tbody></table></div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="caminhões" />
      ) : null}
    </div>
  );
}

function FleetMetric({ icon, label, value, detail }: { readonly icon: "truck" | "gauge" | "planning" | "settings" | "report"; readonly label: string; readonly value: number; readonly detail: string }) {
  return <div className="fleet-metric"><span><Icon name={icon} size={19} /></span><div><p>{label}</p><strong>{value}</strong><small>{detail}</small></div></div>;
}

function FleetStatusCard({ truck }: { readonly truck: TruckOperationalStatus }) {
  const { tone, label, reason } = describeFleetStatus(truck);

  return (
    <tr className={truck.available ? "fleet-card" : "fleet-card fleet-card-off"}>
      <td data-label="Placa"><strong className="fleet-card-plate">{truck.plate}</strong></td>
      <td data-label="Modelo">{truck.model}</td>
      <td data-label="Disponibilidade"><StatusPill tone={tone}>{label}</StatusPill></td>
      <td data-label="Motivo">{reason}</td>
    </tr>
  );
}
