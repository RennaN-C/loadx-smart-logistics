import type { ApiError } from "../types/api";

/**
 * Transforma o 422 do backend em texto que diz QUAL campo está errado.
 *
 * A resposta já trazia a informação e o frontend a descartava: o envelope de
 * erro tem `details` com `{ field, message, type }` por problema, mas a tela
 * só mostrava o `message` de cima — "Os dados informados são inválidos", que
 * não ajuda ninguém a consertar nada.
 *
 * O `message` de dentro do detalhe vem em inglês, do Pydantic ("Input should be
 * greater than 0"). Por isso a tradução sai do `type`, que é estável, e não do
 * texto. O limite numérico, esse sim, é lido da mensagem — é o único lugar
 * onde ele aparece.
 */

interface ValidationDetail {
  readonly field: string;
  readonly message: string;
  readonly type: string;
}

/** Rótulos por campo. A chave é o nome NO BACKEND, em snake_case. */
export type FieldLabels = Readonly<Record<string, string>>;

function isValidationDetail(value: unknown): value is ValidationDetail {
  if (typeof value !== "object" || value === null) return false;

  const candidate = value as Record<string, unknown>;
  return typeof candidate.field === "string" && typeof candidate.type === "string";
}

/** Pydantic só publica o limite dentro da mensagem em inglês. */
function boundOf(message: string): string | null {
  const match = /(-?\d+(?:[.,]\d+)?)/.exec(message);
  return match === null ? null : match[1].replace(".", ",");
}

function describeProblem(detail: ValidationDetail): string {
  const bound = boundOf(detail.message ?? "");

  switch (detail.type) {
    case "missing":
      return "precisa ser preenchido";
    case "string_too_short":
    case "too_short":
      return bound === null ? "está curto demais" : `precisa ter pelo menos ${bound} caractere(s)`;
    case "string_too_long":
    case "too_long":
      return bound === null ? "passou do tamanho permitido" : `passa de ${bound} caractere(s)`;
    case "greater_than":
      return bound === null ? "precisa ser maior" : `precisa ser maior que ${bound}`;
    case "greater_than_equal":
      return bound === null ? "está abaixo do mínimo" : `não pode ser menor que ${bound}`;
    case "less_than":
      return bound === null ? "precisa ser menor" : `precisa ser menor que ${bound}`;
    case "less_than_equal":
      return bound === null ? "está acima do máximo" : `não pode passar de ${bound}`;
    case "int_parsing":
    case "int_type":
      return "precisa ser um número inteiro";
    case "decimal_parsing":
    case "float_parsing":
    case "float_type":
      return "precisa ser um número";
    case "string_pattern_mismatch":
      return "está fora do formato esperado";
    case "datetime_parsing":
    case "datetime_from_date_parsing":
    case "datetime_type":
      return "não é uma data e hora válida";
    case "uuid_parsing":
    case "uuid_type":
      return "não aponta para um registro válido";
    case "bool_parsing":
    case "bool_type":
      return "precisa ser sim ou não";
    case "extra_forbidden":
      return "não é aceito nesta operação";
    case "enum":
      return "tem um valor que não é aceito";
    default:
      // value_error e afins: o backend costuma explicar em português aqui
      return detail.message ? `é inválido (${detail.message})` : "é inválido";
  }
}

/**
 * `items.0.quantity` vira "Quantidade (item 1)". O índice sai do caminho e a
 * busca pelo rótulo usa o caminho SEM ele, senão cada posição da lista exigiria
 * uma entrada própria no mapa.
 */
function describeField(field: string, labels: FieldLabels): string {
  if (field === "") return "Um dos campos";

  const parts = field.split(".");
  const isIndex = (part: string) => /^\d+$/.test(part);
  const indexes = parts.filter(isIndex);
  const key = parts.filter((part) => !isIndex(part)).join(".");
  const label = labels[key] ?? labels[field] ?? key;

  return indexes.length === 0 ? label : `${label} (item ${Number(indexes[0]) + 1})`;
}

/** Quantos problemas listar antes de resumir. Mais que isso vira parede de texto. */
const MAX_LISTED = 3;

/**
 * Devolve a mensagem detalhada, ou `null` quando não é erro de validação — aí
 * quem chamou segue com o mapeamento por código dele.
 */
export function validationMessage(error: ApiError, labels: FieldLabels = {}): string | null {
  if (error.code !== "VALIDATION_ERROR") return null;

  const problems = error.details
    .filter(isValidationDetail)
    .map((detail) => `${describeField(detail.field, labels)} ${describeProblem(detail)}`);

  // sem detalhe não há o que acrescentar; devolve null e mantém o texto original
  const unique = [...new Set(problems)];
  if (unique.length === 0) return null;

  if (unique.length === 1) return `${unique[0]}.`;

  const listed = unique.slice(0, MAX_LISTED).join("; ");
  const rest = unique.length - MAX_LISTED;

  return rest > 0
    ? `Corrija ${unique.length} campos: ${listed}; e mais ${rest}.`
    : `Corrija ${unique.length} campos: ${listed}.`;
}
