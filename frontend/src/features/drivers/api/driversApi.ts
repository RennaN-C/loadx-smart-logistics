import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type { Driver, DriverInput, DriverListItem, DriverOperationalStatus, DriverUpdateInput } from "../types";

/** Resumo da listagem: sem dado pessoal (ver DriverListRead no backend). */
interface DriverListDto {
  id: string;
  name: string;
  license_category: string | null;
  active: boolean;
  created_at: string;
}

interface DriverDto extends DriverListDto {
  document: string;
  phone: string;
  license_number: string;
}

interface DriverOperationalStatusDto {
  id: string;
  name: string;
  license_category: string | null;
  active: boolean;
  has_operation_conflict: boolean;
  available: boolean;
}

export function mapDriverListItemFromDto(dto: DriverListDto): DriverListItem {
  return {
    id: dto.id,
    name: dto.name,
    licenseCategory: dto.license_category,
    active: dto.active,
    createdAt: dto.created_at,
  };
}

export function mapDriverOperationalStatusFromDto(
  dto: DriverOperationalStatusDto,
): DriverOperationalStatus {
  return {
    id: dto.id,
    name: dto.name,
    licenseCategory: dto.license_category,
    active: dto.active,
    hasOperationConflict: dto.has_operation_conflict,
    available: dto.available,
  };
}

export function mapDriverFromDto(dto: DriverDto): Driver {
  return {
    ...mapDriverListItemFromDto(dto),
    document: dto.document,
    phone: dto.phone,
    licenseNumber: dto.license_number,
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

export async function listDrivers(params: ListParams = {}): Promise<Page<DriverListItem>> {
  const { data } = await api.get<PageDto<DriverListDto>>("/drivers", { params: { ...toPageQuery(params), ...(params.archiveStatus ? { archive_status: params.archiveStatus } : {}) } });

  return mapPageFromDto(data, mapDriverListItemFromDto);
}

export async function listDriverOperationalStatus(
  params: ListParams = {},
): Promise<Page<DriverOperationalStatus>> {
  const { data } = await api.get<PageDto<DriverOperationalStatusDto>>(
    "/drivers/operational-status",
    { params: toPageQuery(params) },
  );

  return mapPageFromDto(data, mapDriverOperationalStatusFromDto);
}

/** Necessário para editar: a listagem não traz os campos pessoais. */
export async function getDriver(id: string): Promise<Driver> {
  const { data } = await api.get<DriverDto>(`/drivers/${id}`);

  return mapDriverFromDto(data);
}

export async function createDriver(input: DriverInput): Promise<Driver> {
  const { data } = await api.post<DriverDto>("/drivers", mapDriverToDto(input));

  return mapDriverFromDto(data);
}

export async function updateDriver(id: string, input: DriverUpdateInput): Promise<Driver> {
  const { data } = await api.patch<DriverDto>(`/drivers/${id}`, mapDriverToDto(input));

  return mapDriverFromDto(data);
}
