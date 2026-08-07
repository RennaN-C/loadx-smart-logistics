import { api } from "../../../services/api";
import type { Customer, CustomerInput, CustomerUpdateInput } from "../types";

interface CustomerDto {
  id: string;
  name: string;
  document: string;
  phone: string | null;
  address: string;
  city: string;
  state: string;
  notes: string | null;
  created_at: string;
}

export function mapCustomerFromDto(dto: CustomerDto): Customer {
  return {
    id: dto.id,
    name: dto.name,
    document: dto.document,
    phone: dto.phone,
    address: dto.address,
    city: dto.city,
    state: dto.state,
    notes: dto.notes,
    createdAt: dto.created_at,
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

export async function listCustomers(): Promise<Customer[]> {
  const { data } = await api.get<CustomerDto[]>("/customers");

  return data.map(mapCustomerFromDto);
}

export async function createCustomer(input: CustomerInput): Promise<Customer> {
  const { data } = await api.post<CustomerDto>("/customers", mapCustomerToDto(input));

  return mapCustomerFromDto(data);
}

export async function updateCustomer(id: string, input: CustomerUpdateInput): Promise<Customer> {
  const { data } = await api.patch<CustomerDto>(`/customers/${id}`, mapCustomerToDto(input));

  return mapCustomerFromDto(data);
}
