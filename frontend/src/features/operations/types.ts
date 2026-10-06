/**
 * Indicadores operacionais (OC69), lidos em `GET /operational-indicators`.
 *
 * `CONFIRMADO`: todos os números são calculados no BACKEND, em tempo de leitura.
 * Nenhum é persistido e nenhum é derivado aqui — a OC69 deixou de fora taxas,
 * percentuais, médias e séries históricas de propósito, por não existir contrato
 * de dados uniforme para eles nesta versão. Inventar uma porcentagem na tela
 * seria justamente o que a OC74 põe fora de escopo.
 *
 * O `period` vem do próprio contrato e precisa aparecer na tela: "2 em rota" sem
 * dizer de quando significa coisas diferentes.
 */

/** Situação neste instante, não acumulado. */
export type SnapshotPeriod = "CURRENT_SNAPSHOT";
/** Tudo o que já foi registrado; a v1.1.0 não tem filtro temporal. */
export type AllTimePeriod = "ALL_TIME";

export interface FleetIndicators {
  period: SnapshotPeriod;
  total: number;
  active: number;
  inactive: number;
  available: number;
  unavailable: number;
  withOperationConflict: number;
}

export interface TripIndicators {
  period: AllTimePeriod;
  total: number;
  scheduled: number;
  inRoute: number;
  finished: number;
}

export interface DeliveryIndicators {
  period: AllTimePeriod;
  total: number;
  pending: number;
  inDelivery: number;
  delivered: number;
}

export interface OccurrenceIndicators {
  period: AllTimePeriod;
  total: number;
}

export interface OperationalIndicators {
  fleet: FleetIndicators;
  trips: TripIndicators;
  deliveries: DeliveryIndicators;
  occurrences: OccurrenceIndicators;
}
