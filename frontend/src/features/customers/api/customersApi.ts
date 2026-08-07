import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type { Customer, CustomerInput, CustomerListItem, CustomerUpdateInput } from "../types";

/** Resumo da listagem: sem dado pessoal (ver CustomerListRead no backend). */
interface CustomerListDto {
  id: string;
  name: string;
  city: string;
  state: string;
  created_at: string;
}

interface CustomerDto extends CustomerListDto {
  document: string;
  phone: string | null;
  address: string;
  notes: string | null;
}

export function mapCustomerListItemFromDto(dto: CustomerListDto): CustomerListItem {
  return {
    id: dto.id,
    name: dto.name,
    city: dto.city,
    state: dto.state,
    createdAt: dto.created_at,
  };
}

export function mapCustomerFromDto(dto: CustomerDto): Customer {
  return {
    ...mapCustomerListItemFromDto(dto),
    document: dto.document,
    phone: dto.phone,
    address: dto.address,
    notes: dto.notes,
  };
}

function mapCustomerToDto(input: CustomerUpdateInput): Partial<CustomerDto> {
  const dto: Partial<CustomerDto> = {};

  if (input.name !== undefined) dto.name = input.name;
  if (input.document !== undefined) dto.document = input.document;
  if (input.phone !== undefined) dto.phone = input.phone;
  if (input.address !== undefined) dto.address = input.address;
  if (input.city !== undefined) dto.city = input.city;
  if (input.state !== undefined) dto.state = input.state;
  if (input.notes !== undefined) dto.notes = input.notes;

  return dto;
}

export async function listCustomers(params: ListParams = {}): Promise<Page<CustomerListItem>> {
  const { data } = await api.get<PageDto<CustomerListDto>>("/customers", {
    params: toPageQuery(params),
  });

  return mapPageFromDto(data, mapCustomerListItemFromDto);
}

/** Necessário para editar: a listagem não traz os campos pessoais. */
export async function getCustomer(id: string): Promise<Customer> {
  const { data } = await api.get<CustomerDto>(`/customers/${id}`);

  return mapCustomerFromDto(data);
}

export async function createCustomer(input: CustomerInput): Promise<Customer> {
  const { data } = await api.post<CustomerDto>("/customers", mapCustomerToDto(input));

  return mapCustomerFromDto(data);
}

export async function updateCustomer(id: string, input: CustomerUpdateInput): Promise<Customer> {
  const { data } = await api.patch<CustomerDto>(`/customers/${id}`, mapCustomerToDto(input));

  return mapCustomerFromDto(data);
}
