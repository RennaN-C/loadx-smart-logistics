import { api } from "../../../services/api";
import type { OperationalIndicators } from "../types";

/**
 * `GET /operational-indicators` (OC69).
 *
 * Resposta única e aninhada, sem envelope de paginação: é um retrato, não uma
 * coleção. Lida por `ADMIN` e `LOGISTICS_MANAGER`; `CHECKER` e `DRIVER` não têm
 * acesso ao painel global.
 *
 * Base vazia responde `200` com todos os contadores em zero — o backend não
 * trata ausência de dados como erro, e a tela não deve tratar também.
 */
interface OperationalIndicatorsDto {
  fleet: {
    period: "CURRENT_SNAPSHOT";
    total: number;
    active: number;
    inactive: number;
    available: number;
    unavailable: number;
    with_operation_conflict: number;
  };
  trips: {
    period: "ALL_TIME";
    total: number;
    scheduled: number;
    in_route: number;
    finished: number;
  };
  deliveries: {
    period: "ALL_TIME";
    total: number;
    pending: number;
    in_delivery: number;
    delivered: number;
  };
  occurrences: {
    period: "ALL_TIME";
    total: number;
  };
}

export async function getOperationalIndicators(): Promise<OperationalIndicators> {
  const { data } = await api.get<OperationalIndicatorsDto>("/operational-indicators");

  return {
    fleet: {
      period: data.fleet.period,
      total: data.fleet.total,
      active: data.fleet.active,
      inactive: data.fleet.inactive,
      available: data.fleet.available,
      unavailable: data.fleet.unavailable,
      withOperationConflict: data.fleet.with_operation_conflict,
    },
    trips: {
      period: data.trips.period,
      total: data.trips.total,
      scheduled: data.trips.scheduled,
      inRoute: data.trips.in_route,
      finished: data.trips.finished,
    },
    deliveries: {
      period: data.deliveries.period,
      total: data.deliveries.total,
      pending: data.deliveries.pending,
      inDelivery: data.deliveries.in_delivery,
      delivered: data.deliveries.delivered,
    },
    occurrences: {
      period: data.occurrences.period,
      total: data.occurrences.total,
    },
  };
}
