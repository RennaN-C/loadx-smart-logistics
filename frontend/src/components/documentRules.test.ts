import { describe, expect, it } from "vitest";

import {
  DOCUMENT_MESSAGES,
  isValidCnh,
  isValidCnpj,
  isValidCpf,
  validateCnh,
  validateCustomerDocument,
  validateDriverDocument,
  validatePhone,
} from "./documentRules";

/**
 * Os valores abaixo são EXATAMENTE os de
 * `backend/tests/unit/test_registration_validators.py`.
 *
 * É de propósito: a OC71 só cumpre o que promete se os dois lados derem o mesmo
 * veredito para a mesma entrada. Copiar os vetores é o que transforma isso em
 * teste, em vez de intenção. São documentos fictícios, como exige o AGENTS.md.
 */

describe("CPF", () => {
  it.each(["12345678909", "98765432100", "123.456.789-09"])("aceita %s", (valor) => {
    expect(isValidCpf(valor)).toBe(true);
  });

  it.each(["12345678919", "12345678908", "00000000000", "111.111.111-11"])(
    "recusa %s",
    (valor) => {
      expect(isValidCpf(valor)).toBe(false);
    },
  );

  it("recusa tamanho diferente de 11", () => {
    expect(isValidCpf("1234567890")).toBe(false);
  });
});

describe("CNPJ", () => {
  it.each(["00000000000191", "00000000000272", "00.000.000/0001-91"])(
    "aceita %s",
    (valor) => {
      expect(isValidCnpj(valor)).toBe(true);
    },
  );

  it.each(["00000000000181", "00000000000190", "00000000000000", "11.111.111/1111-11"])(
    "recusa %s",
    (valor) => {
      expect(isValidCnpj(valor)).toBe(false);
    },
  );
});

describe("CNH", () => {
  // Os três últimos cobrem o resto 10 no primeiro dígito, que é onde entra o
  // desconto de 2 — o trecho que exige resto positivo e não existe no CPF.
  it.each(["12345678900", "98765432109", "12340004909", "12340005700", "12340003008"])(
    "aceita %s",
    (valor) => {
      expect(isValidCnh(valor)).toBe(true);
    },
  );

  it.each(["12345678910", "12345678901", "12340004900", "00000000000", "11111111111"])(
    "recusa %s",
    (valor) => {
      expect(isValidCnh(valor)).toBe(false);
    },
  );

  it("não deixa o resto negativo virar outro dígito que o backend", () => {
    // `00000000012`: a base soma zero e o desconto levaria a -2. Em JavaScript
    // cru isso daria -2; no backend dá 9. Se os dois discordarem aqui, discordam
    // em produção.
    expect(isValidCnh("00000000012")).toBe(false);
  });
});

describe("validateCustomerDocument", () => {
  it("aceita CPF e CNPJ válidos", () => {
    expect(validateCustomerDocument("123.456.789-09")).toBeNull();
    expect(validateCustomerDocument("00.000.000/0001-91")).toBeNull();
  });

  it("separa incompleto de inválido, que são problemas diferentes", () => {
    expect(validateCustomerDocument("123")).toMatch(/incompleto/i);
    expect(validateCustomerDocument("12345678908")).toBe(DOCUMENT_MESSAGES.cpf);
    expect(validateCustomerDocument("00000000000190")).toBe(DOCUMENT_MESSAGES.cnpj);
  });

  it("cobra o campo quando está vazio", () => {
    expect(validateCustomerDocument("")).toMatch(/Informe o CPF ou CNPJ/);
  });
});

describe("validateDriverDocument", () => {
  it("aceita CPF", () => {
    expect(validateDriverDocument("12345678909")).toBeNull();
  });

  it("não aceita CNPJ, porque motorista é pessoa física", () => {
    expect(validateDriverDocument("00000000000191")).toMatch(/incompleto/i);
  });
});

describe("validateCnh", () => {
  it("aceita a CNH válida e recusa a inválida", () => {
    expect(validateCnh("12345678900")).toBeNull();
    expect(validateCnh("12345678901")).toBe(DOCUMENT_MESSAGES.cnh);
  });
});

describe("validatePhone", () => {
  it.each(["1130000000", "11900000000", "(11) 3000-0000", "(11) 90000-0000"])(
    "aceita %s",
    (valor) => {
      expect(validatePhone(valor, { required: true })).toBeNull();
    },
  );

  it("explica o DDD zerado em vez de dizer só que está inválido", () => {
    expect(validatePhone("0130000000", { required: true })).toBe(DOCUMENT_MESSAGES.phoneDdd);
  });

  it("explica o celular sem o 9", () => {
    expect(validatePhone("11800000000", { required: true })).toBe(
      DOCUMENT_MESSAGES.phoneMobile,
    );
  });

  it("recusa tamanho fora de 10 e 11", () => {
    expect(validatePhone("119000000", { required: true })).toBe(DOCUMENT_MESSAGES.phone);
  });

  it("vazio só é erro quando o campo é obrigatório", () => {
    expect(validatePhone("", { required: false })).toBeNull();
    expect(validatePhone("", { required: true })).toMatch(/Informe o telefone/);
  });
});
