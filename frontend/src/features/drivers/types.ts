/**
 * A listagem devolve um resumo (`DriverListRead`), sem documento, telefone nem
 * número da CNH — dado pessoal só sai no detalhe. Por isso os dois tipos: o card
 * usa `DriverListItem`, o formulário exige `Driver` completo, buscado por
 * `GET /drivers/{id}` na hora de editar.
 */
export interface DriverListItem {
  id: string;
  name: string;
  /** Categoria da CNH, normalizada em maiúsculas pelo backend. */
  licenseCategory: string | null;
  active: boolean;
  createdAt: string;
}

export interface Driver extends DriverListItem {
  document: string;
  phone: string;
  licenseNumber: string;
}

/** Criação não expõe `active`: o backend já assume `true`. */
export interface DriverInput {
  name: string;
  document: string;
  phone: string;
  licenseNumber: string;
  licenseCategory: string | null;
}

export type DriverUpdateInput = Partial<DriverInput> & { active?: boolean };
