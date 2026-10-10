import { api } from "../../../services/api";

// Contrato institucional isolado: nomes preservam o schema HTTP público.
export interface CompanyProfileInput {
  legal_name: string;
  display_name: string;
  cnpj: string | null;
  phone: string | null;
  email: string | null;
  logo_reference: string | null;
}
export interface CompanyProfile extends CompanyProfileInput {
  id: string;
  created_at: string;
  updated_at: string;
}
export async function getCompanyProfile(): Promise<CompanyProfile | null> {
  const { data } = await api.get<CompanyProfile | null>("/company-profile");
  return data;
}
export async function updateCompanyProfile(input: CompanyProfileInput): Promise<CompanyProfile> {
  const { data } = await api.put<CompanyProfile>("/company-profile", input);
  return data;
}
