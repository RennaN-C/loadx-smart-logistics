import type { ApiError } from "../../../types/api";

export function mapTripErrorToMessage(error: ApiError): string {
  if (error.code === "TRIP_NOT_FOUND") {
    return "Esta viagem não foi encontrada.";
  }

  if (error.code === "TRIP_LOAD_PLAN_NOT_FOUND") {
    return "O plano de carga desta viagem não existe mais.";
  }

  if (error.code === "TRIP_LOAD_PLAN_NOT_APPROVED") {
    return "Só um plano de carga aprovado vira viagem. Aprove o plano antes.";
  }

  if (error.code === "TRIP_LOAD_PLAN_ALREADY_ASSIGNED") {
    return "Este plano de carga já está em outra viagem.";
  }

  if (error.code === "TRIP_DRIVER_NOT_FOUND") {
    return "O motorista selecionado não existe mais. Atualize a lista e escolha outro.";
  }

  if (error.code === "TRIP_DRIVER_INACTIVE") {
    return "Este motorista está inativo e não pode assumir a viagem.";
  }

  if (error.code === "TRIP_LOADING_NOT_FINISHED") {
    return "O carregamento deste plano ainda não foi finalizado.";
  }

  if (error.code === "TRIP_DELIVERIES_NOT_FINISHED") {
    return "Ainda há entregas em aberto. A viagem só finaliza com todas concluídas.";
  }

  if (error.code === "TRIP_STATUS_TRANSITION_NOT_ALLOWED") {
    return "Esta mudança não é permitida a partir da situação atual da viagem.";
  }

  if (error.code === "TRIP_ORDER_NOT_ELIGIBLE" || error.code === "TRIP_ORDER_ALREADY_ASSIGNED") {
    return "Um dos pedidos do plano não pode entrar nesta viagem. Revise o plano de carga.";
  }

  if (error.code === "TRIP_DELIVERY_SEQUENCE_CONFLICT") {
    return "Há conflito na ordem das entregas deste plano. Recalcule o plano de carga.";
  }

  if (error.code === "DELIVERY_NOT_FOUND") {
    return "Esta entrega não foi encontrada.";
  }

  if (error.code === "DELIVERY_TRIP_NOT_IN_ROUTE") {
    return "A viagem precisa estar em rota para movimentar as entregas.";
  }

  if (error.code === "DELIVERY_STATUS_TRANSITION_NOT_ALLOWED") {
    return "Esta mudança não é permitida a partir da situação atual da entrega.";
  }

  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não tem permissão para esta ação, ou esta viagem não é sua.";
  }

  return error.message;
}
