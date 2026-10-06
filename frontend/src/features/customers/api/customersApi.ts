import { onlyDigits } from "../../../components/masks";
import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type {
  CepAddress,
  Customer,
  CustomerInput,
  CustomerListItem,
  CustomerUpdateInput,
} from "../types";

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

interface CepAddressDto {
  cep: string;
  street: string | null;
  neighborhood: string | null;
  complement: string | null;
  city: string;
  state: string;
}

/**
 * Consulta de endereço por CEP (OC70), passando pelo BACKEND.
 *
 * `CONFIRMADO`: o ViaCEP nunca é chamado direto do navegador. Quem fala com ele
 * é `app/integrations/viacep`, que normaliza o CEP, aplica timeout de 5s por
 * fase e traduz as falhas para códigos estáveis. Chamar o serviço externo daqui
 * furaria essa fronteira e exporia a aplicação ao formato cru dele.
 *
 * A rota exige `LOGISTICS_MANAGER` — o mesmo perfil que já é o único a abrir
 * este formulário, então não há caminho em que o botão apareça e responda 403.
 *
 * O caminho leva só dígitos: o backend aceita com hífen, mas mandar o que está
 * na tela faria a URL variar conforme a pontuação digitada.
 */
export async function lookupAddressByCep(cep: string): Promise<CepAddress> {
  const { data } = await api.get<CepAddressDto>(`/customers/cep/${onlyDigits(cep)}`);

  return {
    cep: data.cep,
    street: data.street,
    neighborhood: data.neighborhood,
    complement: data.complement,
    city: data.city,
    state: data.state,
  };
}
