export interface Driver {
  id: string;
  name: string;
  document: string;
  phone: string;
  licenseNumber: string;
  /** Categoria da CNH, normalizada em maiúsculas pelo backend. */
  licenseCategory: string | null;
  active: boolean;
  createdAt: string;
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
