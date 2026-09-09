/**
 * Máscaras de entrada. Funções puras: recebem o que a pessoa digitou e devolvem
 * o texto formatado, sem tocar em DOM nem em estado.
 *
 * A formatação é PROGRESSIVA — "123" vira "123", "1234" vira "123.4" — porque
 * máscara que só aparece no fim faz o campo dar um pulo visual ao completar, e
 * quem está digitando perde a referência de onde estava.
 *
 * `CONFIRMADO`: o backend guarda `document` e `phone` como texto livre de até
 * 32 caracteres, sem validar formato (`customers/schemas.py`). Por isso o que
 * viaja para a API são os DÍGITOS, sem pontuação: a unicidade do documento é
 * comparada como string, e gravar ora com máscara ora sem deixaria dois
 * cadastros do mesmo CPF passarem como distintos.
 */

export function onlyDigits(value: string): string {
  return value.replace(/\D/g, "");
}

/** 11 dígitos é CPF; acima disso, CNPJ. */
const CPF_LENGTH = 11;
const CNPJ_LENGTH = 14;

export function maskDocument(value: string): string {
  const digits = onlyDigits(value).slice(0, CNPJ_LENGTH);

  if (digits.length <= CPF_LENGTH) {
    return digits
      .replace(/^(\d{3})(\d)/, "$1.$2")
      .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/^(\d{3})\.(\d{3})\.(\d{3})(\d)/, "$1.$2.$3-$4");
  }

  return digits
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/^(\d{2})\.(\d{3})\.(\d{3})(\d)/, "$1.$2.$3/$4")
    .replace(/^(\d{2})\.(\d{3})\.(\d{3})\/(\d{4})(\d)/, "$1.$2.$3/$4-$5");
}

/**
 * Fixo tem 10 dígitos e celular 11. A diferença muda onde entra o hífen, então
 * a máscara só decide isso quando o décimo primeiro dígito chega.
 */
export function maskPhone(value: string): string {
  const digits = onlyDigits(value).slice(0, 11);

  if (digits.length <= 10) {
    return digits
      .replace(/^(\d{2})(\d)/, "($1) $2")
      .replace(/^\((\d{2})\) (\d{4})(\d)/, "($1) $2-$3");
  }

  return digits.replace(/^(\d{2})(\d{5})(\d)/, "($1) $2-$3");
}

/**
 * Só o TAMANHO, de propósito: sem dígito verificador.
 *
 * Conferir o dígito recusaria documentos fictícios de teste e de demonstração,
 * e o backend também não confere — o frontend não pode ser mais rígido que o
 * contrato, senão passa a rejeitar cadastro que a API aceitaria.
 */
export function isCompleteDocument(value: string): boolean {
  const length = onlyDigits(value).length;
  return length === CPF_LENGTH || length === CNPJ_LENGTH;
}

/** Aceita fixo (10) e celular (11). */
export function isCompletePhone(value: string): boolean {
  const length = onlyDigits(value).length;
  return length === 10 || length === 11;
}

/** Qual documento o que foi digitado já parece ser; `null` enquanto é curto. */
export function documentKind(value: string): "CPF" | "CNPJ" | null {
  const length = onlyDigits(value).length;
  if (length === CPF_LENGTH) return "CPF";
  if (length === CNPJ_LENGTH) return "CNPJ";
  return null;
}
