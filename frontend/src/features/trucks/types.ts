export interface Truck {
  id: string;
  plate: string;
  model: string;
  internalWidthCm: number;
  internalHeightCm: number;
  internalLengthCm: number;
  maxWeightKg: number;
  active: boolean;
  createdAt: string;
}

/** Criação não expõe `active`: o backend já assume `true`. */
export interface TruckInput {
  plate: string;
  model: string;
  internalWidthCm: number;
  internalHeightCm: number;
  internalLengthCm: number;
  maxWeightKg: number;
}

export type TruckUpdateInput = Partial<TruckInput> & { active?: boolean };

/**
 * Situação operacional do caminhão (OC68), lida em `GET /trucks/operational-status`.
 *
 * `CONFIRMADO`: `available` vem CALCULADO do backend — é `active && !conflito`,
 * decidido em `fleet/service.py`. O frontend não refaz essa conta: `active` e
 * `hasOperationConflict` entram aqui só para EXPLICAR por que um caminhão não
 * está disponível.
 */
export interface TruckOperationalStatus {
  id: string;
  plate: string;
  model: string;
  /** Estado cadastral. Caminhão arquivado sai da operação. */
  active: boolean;
  /** Já comprometido com outra operação, pela regra da OC64. */
  hasOperationConflict: boolean;
  available: boolean;
}
