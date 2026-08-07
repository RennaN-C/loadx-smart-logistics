import { api } from "../../../services/api";
import type { Truck, TruckInput, TruckUpdateInput } from "../types";

interface TruckDto {
  id: string;
  plate: string;
  model: string;
  internal_width_cm: number;
  internal_height_cm: number;
  internal_length_cm: number;
  /** Decimal no backend: pode chegar como número ou como string, dependendo da serialização. */
  max_weight_kg: number | string;
  active: boolean;
  created_at: string;
}

export function mapTruckFromDto(dto: TruckDto): Truck {
  return {
    id: dto.id,
    plate: dto.plate,
    model: dto.model,
    internalWidthCm: dto.internal_width_cm,
    internalHeightCm: dto.internal_height_cm,
    internalLengthCm: dto.internal_length_cm,
    maxWeightKg: Number(dto.max_weight_kg),
    active: dto.active,
    createdAt: dto.created_at,
  };
}

function mapTruckToDto(input: TruckUpdateInput): Partial<TruckDto> {
  const dto: Partial<TruckDto> = {};

  if (input.plate !== undefined) dto.plate = input.plate;
  if (input.model !== undefined) dto.model = input.model;
  if (input.internalWidthCm !== undefined) dto.internal_width_cm = input.internalWidthCm;
  if (input.internalHeightCm !== undefined) dto.internal_height_cm = input.internalHeightCm;
  if (input.internalLengthCm !== undefined) dto.internal_length_cm = input.internalLengthCm;
  if (input.maxWeightKg !== undefined) dto.max_weight_kg = input.maxWeightKg;
  if (input.active !== undefined) dto.active = input.active;

  return dto;
}

export async function listTrucks(): Promise<Truck[]> {
  const { data } = await api.get<TruckDto[]>("/trucks");

  return data.map(mapTruckFromDto);
}

export async function createTruck(input: TruckInput): Promise<Truck> {
  const { data } = await api.post<TruckDto>("/trucks", mapTruckToDto(input));

  return mapTruckFromDto(data);
}

export async function updateTruck(id: string, input: TruckUpdateInput): Promise<Truck> {
  const { data } = await api.patch<TruckDto>(`/trucks/${id}`, mapTruckToDto(input));

  return mapTruckFromDto(data);
}
