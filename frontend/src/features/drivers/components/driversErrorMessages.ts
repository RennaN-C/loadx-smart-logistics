import type { ApiError } from "../../../types/api";

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

  return error.message;
}
