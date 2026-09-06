import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { FieldLabels } from "../../../services/validationErrors";
import type { ApiError } from "../../../types/api";

/** Nome do campo no backend -> rótulo da tela, para o 422 dizer QUAL campo. */
const DRIVER_FIELDS: FieldLabels = {
  name: "Nome",
  document: "Documento",
  phone: "Telefone",
  license_number: "Número da CNH",
  license_category: "Categoria da CNH",
  active: "Ativo",
};

export function mapDriverErrorToMessage(error: ApiError): string {
  if (error.code === "DRIVER_DOCUMENT_ALREADY_EXISTS") {
    return "Já existe um motorista cadastrado com este documento.";
  }

  if (error.code === "DRIVER_LICENSE_NUMBER_ALREADY_EXISTS") {
    return "Já existe um motorista cadastrado com este número de CNH.";
  }

  if (error.code === "DRIVER_NOT_FOUND") {
    return "Este motorista não foi encontrado. Atualize a lista e tente novamente.";
  }

  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não tem permissão para ver ou alterar motoristas.";
  }

  return fallbackErrorMessage(error, DRIVER_FIELDS);
}
