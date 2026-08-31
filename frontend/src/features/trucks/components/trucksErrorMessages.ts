import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { FieldLabels } from "../../../services/validationErrors";
import type { ApiError } from "../../../types/api";

/** Nome do campo no backend -> rótulo da tela, para o 422 dizer QUAL campo. */
const TRUCK_FIELDS: FieldLabels = {
  plate: "Placa",
  model: "Modelo",
  internal_width_cm: "Largura do baú",
  internal_height_cm: "Altura do baú",
  internal_length_cm: "Comprimento do baú",
  max_weight_kg: "Capacidade de peso",
  active: "Ativo",
};

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

  return fallbackErrorMessage(error, TRUCK_FIELDS);
}
