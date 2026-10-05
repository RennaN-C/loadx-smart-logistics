import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type {
  Truck,
  TruckInput,
  TruckOperationalStatus,
  TruckUpdateInput,
} from "../types";

interface TruckDto {
  id: string;
  plate: string;
  model: string;
  internal_width_cm: number;
  internal_height_cm: number;
  internal_length_cm: number;
  max_weight_kg: number;
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
    maxWeightKg: dto.max_weight_kg,
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

export function mapTruckPageFromDto(dto: PageDto<TruckDto>): Page<Truck> {
  return mapPageFromDto(dto, mapTruckFromDto);
}

export async function listTrucks(params: ListParams = {}): Promise<Page<Truck>> {
  const { data } = await api.get<PageDto<TruckDto>>("/trucks", { params: toPageQuery(params) });

  return mapTruckPageFromDto(data);
}

export async function createTruck(input: TruckInput): Promise<Truck> {
  const { data } = await api.post<TruckDto>("/trucks", mapTruckToDto(input));

  return mapTruckFromDto(data);
}

export async function updateTruck(id: string, input: TruckUpdateInput): Promise<Truck> {
  const { data } = await api.patch<TruckDto>(`/trucks/${id}`, mapTruckToDto(input));

  return mapTruckFromDto(data);
}

interface TruckOperationalStatusDto {
  id: string;
  plate: string;
  model: string;
  active: boolean;
  has_operation_conflict: boolean;
  available: boolean;
}

function mapOperationalStatusFromDto(dto: TruckOperationalStatusDto): TruckOperationalStatus {
  return {
    id: dto.id,
    plate: dto.plate,
    model: dto.model,
    active: dto.active,
    hasOperationConflict: dto.has_operation_conflict,
    available: dto.available,
  };
}

/**
 * Situação operacional da frota (OC68/OC73).
 *
 * Rota separada de `GET /trucks` porque a resposta é outra: além do cadastro,
 * traz a disponibilidade consolidada pela OC67. Lida por `ADMIN`, `CHECKER` e
 * `LOGISTICS_MANAGER`, o mesmo conjunto que já lê caminhões.
 */
export async function listTruckOperationalStatus(
  params: ListParams = {},
): Promise<Page<TruckOperationalStatus>> {
  const { data } = await api.get<PageDto<TruckOperationalStatusDto>>("/trucks/operational-status", {
    params: toPageQuery(params),
  });

  return mapPageFromDto(data, mapOperationalStatusFromDto);
}
