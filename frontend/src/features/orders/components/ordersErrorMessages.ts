import type { ApiError } from "../../../types/api";

export function mapOrderErrorToMessage(error: ApiError): string {
  if (error.code === "ORDER_NOT_FOUND") {
    return "Este pedido não foi encontrado. Atualize a lista e tente novamente.";
  }

  if (error.code === "ORDER_CUSTOMER_NOT_FOUND") {
    return "O cliente selecionado não existe mais. Atualize a lista e escolha outro.";
  }

  if (error.code === "ORDER_PRODUCT_NOT_FOUND") {
    return "Um dos produtos do pedido não existe mais. Revise os itens.";
  }

  if (error.code === "ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN") {
    return "Os itens deste pedido já estão em um plano de carga e não podem ser alterados.";
  }

  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não tem permissão para esta ação.";
  }

  return error.message;
}
