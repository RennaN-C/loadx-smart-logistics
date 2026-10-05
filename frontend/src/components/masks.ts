/**
 * Máscaras de entrada. Funções puras: recebem o que a pessoa digitou e devolvem
 * o texto formatado, sem tocar em DOM nem em estado.
 *
 * A formatação é PROGRESSIVA — "123" vira "123", "1234" vira "123.4" — porque
 * máscara que só aparece no fim faz o campo dar um pulo visual ao completar, e
 * quem está digitando perde a referência de onde estava.
 *
 * Aqui mora só a APARÊNCIA. A regra de validade é da OC63 e vive em
 * `documentRules.ts`, espelhando `app/shared/validators.py`.
 *
 * `CONFIRMADO`: o que viaja para a API são os DÍGITOS, sem pontuação. A
 * unicidade do documento é comparada como string no backend, e gravar ora com
 * máscara ora sem deixaria dois cadastros do mesmo CPF passarem como distintos.
 *
 * A CNH não aparece aqui de propósito: o padrão da OC63 para ela é
 * `[0-9]{11}`, sem máscara, então o campo só filtra dígito e não há o que
 * formatar.
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
 * CEP. O backend aceita oito dígitos com ou sem hífen (`ViaCEPProvider`), então
 * a pontuação aqui é só conforto de leitura — o que viaja são os dígitos.
 */
export function maskCep(value: string): string {
  const digits = onlyDigits(value).slice(0, 8);

  return digits.replace(/^(\d{5})(\d)/, "$1-$2");
}
