import type { ApiError } from "../types/api";

/**
 * Erros de validação do backend, separados por campo.
 *
 * `CONFIRMADO`: um 422 chega como
 * `{code: "VALIDATION_ERROR", details: [{field, message, type}]}`
 * (`app/core/exceptions.py`). `field` já vem achatado — `body`, `path` e `query`
 * são removidos lá —, então bate com a chave do payload: `document`, `phone`,
 * `license_number`.
 *
 * O frontend valida antes de enviar, então na prática esses 422 são raros. Mas
 * "raro" não é "nunca": enquanto o erro só aparecia na faixa do topo, a pessoa
 * lia "dados inválidos" sem saber QUAL campo consertar.
 */

const VALIDATION_ERROR = "VALIDATION_ERROR";

/**
 * O Pydantic prefixa a mensagem de um validador nosso com isto. Sem tirar, o
 * usuário lê "Value error, Informe um CPF válido."
 */
const PYDANTIC_PREFIX = /^Value error, /;

/**
 * Só `value_error` vem dos validadores da OC63, que escrevem em português.
 * Restrição nativa do Pydantic — tamanho, tipo, campo ausente — responde em
 * INGLÊS ("String should have at most 160 characters"), e isso não vai para a
 * tela. Verificado contra o backend antes de decidir, não suposto.
 */
const TRANSLATED_TYPE = "value_error";

const FALLBACK = "Valor inválido para este campo.";

interface ValidationDetail {
  readonly field: string;
  readonly message: string;
  readonly type: string;
}

function isValidationDetail(value: unknown): value is ValidationDetail {
  if (typeof value !== "object" || value === null) return false;

  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate.field === "string" &&
    typeof candidate.message === "string" &&
    typeof candidate.type === "string"
  );
}

/**
 * Mapa `campo da API` → mensagem exibível. Vazio quando o erro não é de
 * validação, o que deixa o chamador cair na faixa de erro geral.
 */
export function fieldErrorsFromApiError(error: ApiError): Readonly<Record<string, string>> {
  if (error.code !== VALIDATION_ERROR) return {};

  const byField: Record<string, string> = {};

  for (const detail of error.details) {
    // Primeiro erro de cada campo vence: o Pydantic pode reportar mais de um
    // para o mesmo campo, e empilhar dois textos embaixo de um input só confunde.
    if (isValidationDetail(detail) && detail.field !== "" && byField[detail.field] === undefined) {
      byField[detail.field] =
        detail.type === TRANSLATED_TYPE ? detail.message.replace(PYDANTIC_PREFIX, "") : FALLBACK;
    }
  }

  return byField;
}
