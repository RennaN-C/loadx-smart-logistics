import type { ApiError } from "../../../types/api";

export function mapTruckErrorToMessage(error: ApiError): string {
  if (error.code === "TRUCK_PLATE_ALREADY_EXISTS") {
    return "Já existe um caminhão cadastrado com esta placa.";
  }

  if (error.code === "TRUCK_NOT_FOUND") {
    return "Este caminhão não foi encontrado. Atualize a lista e tente novamente.";
  }

  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não tem permissão para esta ação.";
  }

  return error.message;
}
