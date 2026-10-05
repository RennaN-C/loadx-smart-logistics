import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { createDriver, updateDriver } from "../api/driversApi";
import type { Driver } from "../types";
import { DriverForm } from "./DriverForm";
import { mapDriverErrorToMessage } from "./driversErrorMessages";

vi.mock("../api/driversApi");

/**
 * CPF e CNH fictícios COM dígito verificador válido, de
 * `backend/tests/unit/test_registration_validators.py`.
 *
 * Antes da OC71 valia qualquer sequência de 11 dígitos aqui, porque a tela só
 * contava. Agora ela confere o verificador igual ao backend — o que quebrou
 * estes testes e com razão: a API recusaria os valores que eles usavam.
 */
const CPF_VALIDO = "123.456.789-09";
const CPF_OUTRO = "987.654.321-00";
const CNH_VALIDA = "12345678900";
const CNH_OUTRA = "98765432109";

const DRIVER: Driver = {
  id: "d1",
  name: "Carlos Pereira",
  document: CPF_VALIDO,
  phone: "(11) 91111-1111",
  licenseNumber: CNH_VALIDA,
  licenseCategory: "E",
  active: true,
  createdAt: "2026-08-01T12:00:00Z",
};

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("NOME"), { target: { value: "Rita Alves" } });
  fireEvent.change(screen.getByLabelText("DOCUMENTO"), { target: { value: CPF_OUTRO } });
  fireEvent.change(screen.getByLabelText("TELEFONE"), { target: { value: "(11) 92222-2222" } });
  fireEvent.change(screen.getByLabelText("NÚMERO DA CNH"), { target: { value: CNH_OUTRA } });
}

function cadastrar() {
  fireEvent.click(screen.getByRole("button", { name: "Cadastrar motorista" }));
}

describe("mapDriverErrorToMessage", () => {
  it("distingue documento duplicado de CNH duplicada", () => {
    expect(mapDriverErrorToMessage(new ApiError("DRIVER_DOCUMENT_ALREADY_EXISTS", "x"))).toBe(
      "Já existe um motorista cadastrado com este documento.",
    );
    expect(mapDriverErrorToMessage(new ApiError("DRIVER_LICENSE_NUMBER_ALREADY_EXISTS", "x"))).toBe(
      "Já existe um motorista cadastrado com este número de CNH.",
    );
  });
});

describe("DriverForm", () => {
  beforeEach(() => {
    vi.mocked(createDriver).mockReset();
    vi.mocked(updateDriver).mockReset();
  });

  it("mascara documento e telefone, e explica a CNH numa dica", () => {
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("DOCUMENTO"), { target: { value: "12345678901" } });
    expect(screen.getByLabelText("DOCUMENTO")).toHaveValue("123.456.789-01");

    fireEvent.change(screen.getByLabelText("TELEFONE"), { target: { value: "42999998888" } });
    expect(screen.getByLabelText("TELEFONE")).toHaveValue("(42) 99999-8888");

    // a dica da CNH existe porque confundir com CPF é o erro comum
    fireEvent.focus(screen.getByRole("button", { name: "Sobre número da cnh" }));
    expect(screen.getByRole("tooltip")).toHaveTextContent(/Não é o CPF/);
  });

  it("a CNH não aceita pontuação, porque o backend não aceita", () => {
    // O padrão da OC63 para CNH é `[0-9]{11}`, sem máscara. Digitar
    // "012.345.678-90" rendia 422 sem explicação até aqui.
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    const campo = screen.getByLabelText("NÚMERO DA CNH");

    fireEvent.change(campo, { target: { value: "123.456.789-00" } });

    expect(campo).toHaveValue(CNH_VALIDA);
  });

  it("barra documento incompleto antes de chamar a API, no próprio campo", async () => {
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("DOCUMENTO"), { target: { value: "1234" } });

    cadastrar();

    const campo = screen.getByLabelText("DOCUMENTO");
    await waitFor(() => expect(campo).toHaveAccessibleDescription(/Documento incompleto/));
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(createDriver).not.toHaveBeenCalled();
  });

  it("recusa CNH com dígito verificador errado", async () => {
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("NÚMERO DA CNH"), { target: { value: "12345678901" } });

    cadastrar();

    await waitFor(() =>
      expect(screen.getByLabelText("NÚMERO DA CNH")).toHaveAccessibleDescription(
        "Informe uma CNH válida com 11 dígitos.",
      ),
    );
    expect(createDriver).not.toHaveBeenCalled();
  });

  it("não aceita CNPJ no lugar do CPF: motorista é pessoa física", async () => {
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("DOCUMENTO"), { target: { value: "00000000000191" } });

    cadastrar();

    await waitFor(() =>
      expect(screen.getByLabelText("DOCUMENTO")).toHaveAttribute("aria-invalid", "true"),
    );
    expect(createDriver).not.toHaveBeenCalled();
  });

  it("recusa telefone com DDD zerado dizendo o que está errado", async () => {
    // Vazio quem barra é o `required` nativo, antes do nosso handler. O que só a
    // regra da OC63 pega é telefone COMPLETO e inválido, como DDD zerado.
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("TELEFONE"), { target: { value: "0130000000" } });

    cadastrar();

    await waitFor(() =>
      expect(screen.getByLabelText("TELEFONE")).toHaveAccessibleDescription(
        "O DDD não pode começar com zero.",
      ),
    );
    expect(createDriver).not.toHaveBeenCalled();
  });

  it("o telefone do motorista é obrigatório no HTML, diferente do cliente", () => {
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByLabelText("TELEFONE")).toBeRequired();
  });

  it("envia categoria nula quando não é informada", async () => {
    vi.mocked(createDriver).mockResolvedValue(DRIVER);
    const onSaved = vi.fn();

    render(<DriverForm onSaved={onSaved} onCancel={vi.fn()} />);
    fillRequiredFields();
    cadastrar();

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(createDriver).toHaveBeenCalledWith({
      name: "Rita Alves",
      // Só os dígitos: a unicidade do documento é comparada como string no
      // backend, e misturar formatos deixaria duplicata passar.
      document: "98765432100",
      phone: "11922222222",
      licenseNumber: CNH_OUTRA,
      licenseCategory: null,
    });
  });

  it("pousa o 422 do backend no campo que ele apontou", async () => {
    vi.mocked(createDriver).mockRejectedValue(
      new ApiError("VALIDATION_ERROR", "Os dados informados são inválidos.", [
        {
          field: "license_number",
          message: "Value error, Informe uma CNH válida com 11 dígitos.",
          type: "value_error",
        },
      ]),
    );

    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    cadastrar();

    await waitFor(() =>
      expect(screen.getByLabelText("NÚMERO DA CNH")).toHaveAccessibleDescription(
        "Informe uma CNH válida com 11 dígitos.",
      ),
    );
  });

  it("oferece só as categorias que dirigem caminhão", () => {
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);

    const options = [...screen.getByLabelText("CATEGORIA (OPCIONAL)").querySelectorAll("option")].map(
      (option) => option.value,
    );

    expect(options).toEqual(["", "C", "D", "E", "AC", "AD", "AE"]);
  });

  it("só expõe o campo 'ativo' na edição", () => {
    const { unmount } = render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.queryByLabelText(/Motorista ativo/)).not.toBeInTheDocument();
    unmount();

    render(<DriverForm driver={DRIVER} onSaved={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText(/Motorista ativo/)).toBeInTheDocument();
  });

  it("envia active junto na edição", async () => {
    vi.mocked(updateDriver).mockResolvedValue({ ...DRIVER, active: false });
    const onSaved = vi.fn();

    render(<DriverForm driver={DRIVER} onSaved={onSaved} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByLabelText(/Motorista ativo/));
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(updateDriver).toHaveBeenCalledWith(DRIVER.id, expect.objectContaining({ active: false }));
  });
});
