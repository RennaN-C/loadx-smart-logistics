import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { FieldLabels } from "../../../services/validationErrors";
import type { ApiError } from "../../../types/api";

/** Nome do campo no backend -> rótulo da tela, para o 422 dizer QUAL campo. */
const CUSTOMER_FIELDS: FieldLabels = {
  name: "Nome",
  document: "Documento",
  phone: "Telefone",
  address: "Endereço",
  city: "Cidade",
  state: "UF",
  notes: "Observações",
};

export function mapCustomerErrorToMessage(error: ApiError): string {
  if (error.code === "CUSTOMER_DOCUMENT_ALREADY_EXISTS") {
    return "Já existe um cliente cadastrado com este documento.";
  }

  if (error.code === "CUSTOMER_NOT_FOUND") {
    return "Este cliente não foi encontrado. Atualize a lista e tente novamente.";
  }

  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não tem permissão para ver ou alterar clientes.";
  }

  return fallbackErrorMessage(error, CUSTOMER_FIELDS);
}
