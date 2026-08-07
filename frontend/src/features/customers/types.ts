/**
 * A listagem devolve um resumo (`CustomerListRead`), sem documento, telefone,
 * endereço nem observações — dado pessoal só sai no detalhe. Por isso os dois
 * tipos: o card usa `CustomerListItem`, o formulário exige `Customer` completo,
 * buscado por `GET /customers/{id}` na hora de editar.
 */
export interface CustomerListItem {
  id: string;
  name: string;
  city: string;
  /** UF com 2 letras, normalizada em maiúsculas pelo backend. */
  state: string;
  createdAt: string;
}

export interface Customer extends CustomerListItem {
  document: string;
  phone: string | null;
  address: string;
  notes: string | null;
}

export interface CustomerInput {
  name: string;
  document: string;
  phone: string | null;
  address: string;
  city: string;
  state: string;
  notes: string | null;
}

export type CustomerUpdateInput = Partial<CustomerInput>;
