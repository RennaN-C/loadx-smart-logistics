import type { ApiError } from "../../../types/api";

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

  return error.message;
}
