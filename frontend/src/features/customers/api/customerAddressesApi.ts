import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, MAX_PAGE_SIZE, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type { CustomerAddress, CustomerAddressInput, CustomerAddressUpdateInput } from "../types";

interface CustomerAddressDto {
  id: string;
  customer_id: string;
  label: string;
  address: string;
  city: string;
  state: string;
  postal_code: string | null;
  active: boolean;
  is_primary: boolean;
  created_at: string;
}

export function mapCustomerAddress(dto: CustomerAddressDto): CustomerAddress {
  return { id: dto.id, customerId: dto.customer_id, label: dto.label, address: dto.address,
    city: dto.city, state: dto.state, postalCode: dto.postal_code, active: dto.active,
    isPrimary: dto.is_primary, createdAt: dto.created_at };
}

function toDto(input: CustomerAddressUpdateInput): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const key of ["label", "address", "city", "state", "active"] as const) {
    if (input[key] !== undefined) result[key] = input[key];
  }
  if (input.postalCode !== undefined) result.postal_code = input.postalCode;
  if (input.isPrimary !== undefined) result.is_primary = input.isPrimary;
  return result;
}

export async function listCustomerAddresses(customerId: string, params: ListParams = {}): Promise<Page<CustomerAddress>> {
  const { data } = await api.get<PageDto<CustomerAddressDto>>(`/customers/${customerId}/addresses`, {
    params: { ...toPageQuery(params), archive_status: params.archiveStatus ?? "active" },
  });
  return mapPageFromDto(data, mapCustomerAddress);
}

export async function listActiveCustomerAddresses(customerId: string): Promise<CustomerAddress[]> {
  const first = await listCustomerAddresses(customerId, { pageSize: MAX_PAGE_SIZE });
  const items = [...first.items];
  for (let page = 2; page <= first.totalPages; page += 1) {
    const next = await listCustomerAddresses(customerId, { page, pageSize: MAX_PAGE_SIZE });
    items.push(...next.items);
  }
  return items.filter((address) => address.active);
}

export async function createCustomerAddress(customerId: string, input: CustomerAddressInput): Promise<CustomerAddress> {
  const { data } = await api.post<CustomerAddressDto>(`/customers/${customerId}/addresses`, toDto(input));
  return mapCustomerAddress(data);
}

export async function updateCustomerAddress(customerId: string, id: string, input: CustomerAddressUpdateInput): Promise<CustomerAddress> {
  const { data } = await api.patch<CustomerAddressDto>(`/customers/${customerId}/addresses/${id}`, toDto(input));
  return mapCustomerAddress(data);
}
