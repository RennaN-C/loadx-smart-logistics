import { api } from "../../../services/api";
import type { Driver, DriverInput, DriverUpdateInput } from "../types";

interface DriverDto {
  id: string;
  name: string;
  document: string;
  phone: string;
  license_number: string;
  license_category: string | null;
  active: boolean;
  created_at: string;
}

export function mapDriverFromDto(dto: DriverDto): Driver {
  return {
    id: dto.id,
    name: dto.name,
    document: dto.document,
    phone: dto.phone,
    licenseNumber: dto.license_number,
    licenseCategory: dto.license_category,
    active: dto.active,
    createdAt: dto.created_at,
  };
}

function mapDriverToDto(input: DriverUpdateInput): Partial<DriverDto> {
  const dto: Partial<DriverDto> = {};

  if (input.name !== undefined) dto.name = input.name;
  if (input.document !== undefined) dto.document = input.document;
  if (input.phone !== undefined) dto.phone = input.phone;
  if (input.licenseNumber !== undefined) dto.license_number = input.licenseNumber;
  if (input.licenseCategory !== undefined) dto.license_category = input.licenseCategory;
  if (input.active !== undefined) dto.active = input.active;

  return dto;
}

export async function listDrivers(): Promise<Driver[]> {
  const { data } = await api.get<DriverDto[]>("/drivers");

  return data.map(mapDriverFromDto);
}

export async function createDriver(input: DriverInput): Promise<Driver> {
  const { data } = await api.post<DriverDto>("/drivers", mapDriverToDto(input));

  return mapDriverFromDto(data);
}

export async function updateDriver(id: string, input: DriverUpdateInput): Promise<Driver> {
  const { data } = await api.patch<DriverDto>(`/drivers/${id}`, mapDriverToDto(input));

  return mapDriverFromDto(data);
}
