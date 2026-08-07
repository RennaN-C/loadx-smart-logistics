export interface Customer {
  id: string;
  name: string;
  document: string;
  phone: string | null;
  address: string;
  city: string;
  /** UF com 2 letras, normalizada em maiúsculas pelo backend. */
  state: string;
  notes: string | null;
  createdAt: string;
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
