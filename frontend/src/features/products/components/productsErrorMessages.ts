import type { ApiError } from "../../../types/api";

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

  return error.message;
}
