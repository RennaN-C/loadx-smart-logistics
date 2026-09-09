import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { FieldLabels } from "../../../services/validationErrors";
import type { ApiError } from "../../../types/api";

/** Nome do campo no backend -> rótulo da tela, para o 422 dizer QUAL campo. */
const PRODUCT_FIELDS: FieldLabels = {
  code: "Código",
  name: "Nome",
  description: "Descrição",
  width_cm: "Largura",
  height_cm: "Altura",
  length_cm: "Comprimento",
  weight_kg: "Peso",
  fragile: "Frágil",
  stackable: "Empilhável",
  rotation_allowed: "Rotação permitida",
};

export function mapProductErrorToMessage(error: ApiError): string {
  if (error.code === "PRODUCT_CODE_ALREADY_EXISTS") {
    return "Já existe um produto cadastrado com este código.";
  }

  if (error.code === "PRODUCT_NOT_FOUND") {
    return "Este produto não foi encontrado. Atualize a lista e tente novamente.";
  }

  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não tem permissão para esta ação.";
  }

  return fallbackErrorMessage(error, PRODUCT_FIELDS);
}
