import { api } from "../../../services/api";
import type { Page } from "../../../types/api";
import type { Truck, TruckInput, TruckUpdateInput } from "../types";

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

interface PageDto<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

interface ListTrucksParams {
  page?: number;
  pageSize?: number;
  sortOrder?: "asc" | "desc";
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
  return {
    items: dto.items.map(mapTruckFromDto),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
  };
}

export async function listTrucks({
  page = 1,
  pageSize = 20,
  sortOrder = "desc",
}: ListTrucksParams = {}): Promise<Page<Truck>> {
  const { data } = await api.get<PageDto<TruckDto>>("/trucks", {
    params: {
      page,
      page_size: pageSize,
      sort_order: sortOrder,
    },
  });

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
