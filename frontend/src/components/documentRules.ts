import { onlyDigits } from "./masks";

/**
 * Regras de documento e telefone, espelhando a OC63.
 *
 * A autoridade continua sendo o backend (`app/shared/validators.py`): isto aqui
 * existe para o erro aparecer ANTES do envio, não para substituir a validação
 * de lá. Por isso a regra é copiada em vez de inventada — qualquer divergência
 * faria o frontend rejeitar cadastro que a API aceitaria, ou prometer que algo
 * passa e tomar 422 na cara do usuário.
 *
 * As mensagens são as mesmas do backend de propósito. Quem erra o CPF duas
 * vezes — uma na tela, outra na resposta — não deve ler dois textos diferentes
 * para o mesmo problema.
 *
 * `CONFIRMADO`: os vetores de teste são os mesmos de
 * `backend/tests/unit/test_registration_validators.py`, que é o que prova que
 * os dois lados concordam.
 */

const CPF_LENGTH = 11;
const CNPJ_LENGTH = 14;
const CNH_LENGTH = 11;

export const DOCUMENT_MESSAGES = {
  cpf: "Informe um CPF válido.",
  cnpj: "Informe um CNPJ válido.",
  customer: "Informe um CPF ou CNPJ válido.",
  cnh: "Informe uma CNH válida com 11 dígitos.",
  phone: "Informe um telefone com DDD e 10 ou 11 dígitos.",
  phoneDdd: "O DDD não pode começar com zero.",
  phoneMobile: "O celular deve começar com 9 após o DDD.",
} as const;

/**
 * Resto SEMPRE positivo, como o `%` do Python.
 *
 * Não é preciosismo: o dígito da CNH subtrai 2 antes do resto, e em JavaScript
 * `-2 % 11` é `-2`, enquanto no backend é `9`. Sem isto, uma CNH como
 * `00000000012` — que não cai na regra de dígitos repetidos — seria julgada
 * diferente nos dois lados.
 */
function mod(value: number, divisor: number): number {
  return ((value % divisor) + divisor) % divisor;
}

/** `11111111111` e afins são recusados pelo backend antes do cálculo. */
function isRepeatedSequence(digits: string): boolean {
  return new Set(digits).size === 1;
}

function mod11Digit(digits: string, weights: readonly number[]): string {
  const sum = weights.reduce(
    (total, weight, index) => total + Number(digits[index]) * weight,
    0,
  );
  const remainder = sum % 11;

  return String(remainder < 2 ? 0 : 11 - remainder);
}

function descending(from: number, to: number): number[] {
  const weights: number[] = [];
  for (let weight = from; weight >= to; weight -= 1) weights.push(weight);
  return weights;
}

export function isValidCpf(value: string): boolean {
  const digits = onlyDigits(value);
  if (digits.length !== CPF_LENGTH || isRepeatedSequence(digits)) return false;

  const first = mod11Digit(digits.slice(0, 9), descending(10, 2));
  const second = mod11Digit(digits.slice(0, 9) + first, descending(11, 2));

  return digits.slice(-2) === first + second;
}

const CNPJ_FIRST_WEIGHTS = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
const CNPJ_SECOND_WEIGHTS = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

export function isValidCnpj(value: string): boolean {
  const digits = onlyDigits(value);
  if (digits.length !== CNPJ_LENGTH || isRepeatedSequence(digits)) return false;

  const first = mod11Digit(digits.slice(0, 12), CNPJ_FIRST_WEIGHTS);
  const second = mod11Digit(digits.slice(0, 12) + first, CNPJ_SECOND_WEIGHTS);

  return digits.slice(-2) === first + second;
}

/**
 * A CNH não usa módulo 11 como CPF e CNPJ: o primeiro dígito vira zero quando o
 * resto dá 10, e esse caso DESCONTA 2 do segundo cálculo. É o que os vetores
 * `12340004909`, `12340005700` e `12340003008` cobrem.
 */
export function isValidCnh(value: string): boolean {
  const digits = onlyDigits(value);
  if (digits.length !== CNH_LENGTH || isRepeatedSequence(digits)) return false;

  const base = digits.slice(0, 9).split("").map(Number);

  let first = base.reduce((total, digit, index) => total + digit * (9 - index), 0) % 11;
  const discount = first === 10 ? 2 : 0;
  first = first === 10 ? 0 : first;

  const secondSum = base.reduce((total, digit, index) => total + digit * (index + 1), 0);
  let second = mod(secondSum - discount, 11);
  second = second === 10 ? 0 : second;

  return digits.slice(-2) === `${first}${second}`;
}

/**
 * Mensagem do campo, ou `null` quando está válido.
 *
 * Documento curto ganha texto próprio: o backend nunca vê esse estado, porque o
 * formulário barra antes, e "Informe um CPF válido" para quem digitou cinco
 * dígitos esconde que faltam números, não que os dígitos estão errados.
 */
export function validateCustomerDocument(value: string): string | null {
  const digits = onlyDigits(value);

  if (digits.length === 0) return "Informe o CPF ou CNPJ do cliente.";
  if (digits.length !== CPF_LENGTH && digits.length !== CNPJ_LENGTH) {
    return "Documento incompleto. Informe um CPF com 11 dígitos ou um CNPJ com 14.";
  }
  if (digits.length === CPF_LENGTH) {
    return isValidCpf(digits) ? null : DOCUMENT_MESSAGES.cpf;
  }

  return isValidCnpj(digits) ? null : DOCUMENT_MESSAGES.cnpj;
}

/** Motorista é sempre pessoa física: aqui o documento é CPF. */
export function validateDriverDocument(value: string): string | null {
  const digits = onlyDigits(value);

  if (digits.length === 0) return "Informe o CPF do motorista.";
  if (digits.length !== CPF_LENGTH) {
    return "Documento incompleto. Informe um CPF com 11 dígitos.";
  }

  return isValidCpf(digits) ? null : DOCUMENT_MESSAGES.cpf;
}

export function validateCnh(value: string): string | null {
  const digits = onlyDigits(value);

  if (digits.length === 0) return "Informe o número da CNH.";

  return isValidCnh(digits) ? null : DOCUMENT_MESSAGES.cnh;
}

/**
 * `required: false` aceita vazio — telefone de cliente é opcional no contrato,
 * o de motorista não.
 */
export function validatePhone(value: string, options: { required: boolean }): string | null {
  const digits = onlyDigits(value);

  if (digits.length === 0) {
    return options.required ? "Informe o telefone do motorista." : null;
  }
  if (digits.length !== 10 && digits.length !== 11) return DOCUMENT_MESSAGES.phone;
  if (digits.startsWith("0")) return DOCUMENT_MESSAGES.phoneDdd;
  if (digits.length === 11 && digits[2] !== "9") return DOCUMENT_MESSAGES.phoneMobile;

  return null;
}
