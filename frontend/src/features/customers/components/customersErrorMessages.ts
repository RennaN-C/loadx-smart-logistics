import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { FieldLabels } from "../../../services/validationErrors";
import type { ApiError } from "../../../types/api";

/** Nome do campo no backend -> rótulo da tela, para o 422 dizer QUAL campo. */
const CUSTOMER_FIELDS: FieldLabels = {
  name: "Nome",
  document: "Documento",
  phone: "Telefone",
  address: "Endereço",
  city: "Cidade",
  state: "UF",
  notes: "Observações",
};

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

  return fallbackErrorMessage(error, CUSTOMER_FIELDS);
}

/**
 * Falhas da consulta de CEP (OC70).
 *
 * Separado de `mapCustomerErrorToMessage` porque o enquadramento é outro: aqui
 * nada deu errado com o CADASTRO. A consulta é auxílio de preenchimento, e toda
 * mensagem precisa deixar claro que dá para seguir à mão — foi o que a OC62
 * pediu de quem consome: tratar como falha auxiliar, preservar o que já foi
 * digitado e não impedir o cadastro manual.
 *
 * `CONFIRMADO`: os códigos são os de `app/integrations/viacep`. `404` do ViaCEP
 * vira `VIACEP_UNAVAILABLE`, não "não encontrado" — quem sinaliza CEP
 * inexistente é o marcador `erro: true` no corpo, não o status.
 */
const CEP_MESSAGES: Readonly<Record<string, string>> = {
  VIACEP_INVALID_CEP: "CEP inválido. Informe os 8 dígitos.",
  VIACEP_NOT_FOUND: "CEP não encontrado. Confira o número ou preencha o endereço à mão.",
  VIACEP_UNAVAILABLE: "A consulta de CEP está fora do ar. Preencha o endereço à mão.",
  VIACEP_TIMEOUT: "A consulta de CEP demorou demais. Tente de novo ou preencha à mão.",
  VIACEP_INVALID_RESPONSE: "A consulta de CEP devolveu algo inesperado. Preencha o endereço à mão.",
  AUTH_FORBIDDEN: "Seu perfil não pode consultar CEP. Preencha o endereço à mão.",
};

export function mapCepErrorToMessage(error: ApiError): string {
  return CEP_MESSAGES[error.code] ?? "Não foi possível consultar o CEP. Preencha o endereço à mão.";
}
