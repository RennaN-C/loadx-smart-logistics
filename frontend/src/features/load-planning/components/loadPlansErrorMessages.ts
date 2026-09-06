import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { FieldLabels } from "../../../services/validationErrors";
import type { ApiError } from "../../../types/api";

/** Nome do campo no backend -> rótulo da tela, para o 422 dizer QUAL campo. */
const LOAD_PLAN_FIELDS: FieldLabels = {
  truck_id: "Caminhão",
  order_ids: "Pedidos selecionados",
};

export function mapLoadPlanErrorToMessage(error: ApiError): string {
  if (error.code === "LOAD_PLAN_NOT_FOUND") {
    return "Este plano de carga não foi encontrado.";
  }

  if (error.code === "LOAD_PLAN_TRUCK_NOT_FOUND") {
    return "O caminhão selecionado não existe mais. Atualize a lista e escolha outro.";
  }

  if (error.code === "LOAD_PLAN_TRUCK_INACTIVE") {
    return "Este caminhão está inativo e não pode receber carga. Escolha outro ou reative o cadastro.";
  }

  if (error.code === "LOAD_PLAN_ORDER_NOT_FOUND") {
    return "Um dos pedidos selecionados não existe mais. Atualize a lista.";
  }

  if (error.code === "LOAD_PLAN_ORDER_NOT_ELIGIBLE") {
    return "Só pedidos com situação Pronto entram em um plano de carga. Revise a seleção.";
  }

  if (error.code === "LOAD_PLAN_PRODUCT_NOT_FOUND") {
    return "Um dos produtos dos pedidos não existe mais. Revise os pedidos selecionados.";
  }

  if (error.code === "LOAD_PLAN_HAS_REJECTIONS") {
    return "Este plano tem volumes que ficaram de fora e não pode ser aprovado. Recalcule ou ajuste a seleção.";
  }

  if (error.code === "LOAD_PLAN_INVALID_STATUS") {
    return "A situação atual deste plano não permite esta ação.";
  }

  if (error.code === "LOAD_PLAN_SOURCE_CHANGED") {
    return "Os pedidos ou o caminhão mudaram desde o cálculo original. Monte um plano novo.";
  }

  if (error.code === "INVALID_LOAD_PLAN_INPUT") {
    return "Os dados enviados para o cálculo são inválidos. Revise o caminhão e os pedidos.";
  }

  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não tem permissão para esta ação.";
  }

  return fallbackErrorMessage(error, LOAD_PLAN_FIELDS);
}
