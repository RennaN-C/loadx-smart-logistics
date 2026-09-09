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
