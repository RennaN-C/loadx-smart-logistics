import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { createCustomer } from "../api/customersApi";
import type { Customer } from "../types";
import { CustomerForm } from "./CustomerForm";
import { mapCustomerErrorToMessage } from "./customersErrorMessages";

vi.mock("../api/customersApi");

/**
 * Documentos fictícios COM dígito verificador válido, tirados de
 * `backend/tests/unit/test_registration_validators.py`.
 *
 * Antes da OC71 qualquer sequência de 14 dígitos servia aqui, porque a tela só
 * contava dígitos. Agora ela confere o verificador igual ao backend, então um
 * valor inventado faria o teste falhar — e falharia com razão, porque a API
 * também o recusaria.
 */
const CNPJ_VALIDO = "00.000.000/0001-91";
const CNPJ_VALIDO_DIGITOS = "00000000000191";
const CNPJ_OUTRO = "00.000.000/0002-72";

const CUSTOMER: Customer = {
  id: "c1",
  name: "Distribuidora Aurora",
  document: CNPJ_OUTRO,
  phone: null,
  address: "Rua das Palmeiras, 120",
  city: "Campinas",
  state: "SP",
  notes: null,
  createdAt: "2026-08-01T12:00:00Z",
};

function fillRequiredFields(document = CNPJ_VALIDO) {
  fireEvent.change(screen.getByLabelText("NOME OU RAZÃO SOCIAL"), {
    target: { value: "Mercado Central" },
  });
  fireEvent.change(screen.getByLabelText("DOCUMENTO"), { target: { value: document } });
  fireEvent.change(screen.getByLabelText("ENDEREÇO"), { target: { value: "Av. Brasil, 500" } });
  fireEvent.change(screen.getByLabelText("CIDADE"), { target: { value: "Sorocaba" } });
  fireEvent.change(screen.getByLabelText("UF"), { target: { value: "sp" } });
}

function enviar() {
  fireEvent.click(screen.getByRole("button", { name: "Cadastrar cliente" }));
}

describe("mapCustomerErrorToMessage", () => {
  it("traduz CUSTOMER_DOCUMENT_ALREADY_EXISTS", () => {
    expect(mapCustomerErrorToMessage(new ApiError("CUSTOMER_DOCUMENT_ALREADY_EXISTS", "conflito"))).toBe(
      "Já existe um cliente cadastrado com este documento.",
    );
  });

  it("usa a mensagem do backend para qualquer outro código", () => {
    expect(mapCustomerErrorToMessage(new ApiError("VALIDATION_ERROR", "Dados inválidos."))).toBe(
      "Dados inválidos.",
    );
  });
});

describe("CustomerForm", () => {
  beforeEach(() => {
    vi.mocked(createCustomer).mockReset();
  });

  it("normaliza a UF em maiúsculas e envia telefone e observações nulos quando vazios", async () => {
    vi.mocked(createCustomer).mockResolvedValue(CUSTOMER);
    const onSaved = vi.fn();

    render(<CustomerForm onSaved={onSaved} onCancel={vi.fn()} />);
    fillRequiredFields();
    enviar();

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(createCustomer).toHaveBeenCalledWith({
      name: "Mercado Central",
      // Só os dígitos: com pontuação, o mesmo CNPJ entraria duas vezes,
      // porque a unicidade no backend compara a string crua.
      document: CNPJ_VALIDO_DIGITOS,
      phone: null,
      address: "Av. Brasil, 500",
      city: "Sorocaba",
      state: "SP",
      notes: null,
    });
  });

  it("aplica a máscara enquanto o documento é digitado", () => {
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    const campo = screen.getByLabelText("DOCUMENTO");

    fireEvent.change(campo, { target: { value: "12345678901" } });
    expect(campo).toHaveValue("123.456.789-01");

    fireEvent.change(campo, { target: { value: "12345678000199" } });
    expect(campo).toHaveValue("12.345.678/0001-99");
  });

  it("aplica a máscara no telefone", () => {
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    const campo = screen.getByLabelText("TELEFONE (OPCIONAL)");

    fireEvent.change(campo, { target: { value: "42999998888" } });
    expect(campo).toHaveValue("(42) 99999-8888");
  });

  it("a máscara é só aparência: o que viaja são os dígitos", async () => {
    vi.mocked(createCustomer).mockResolvedValue(CUSTOMER);

    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("TELEFONE (OPCIONAL)"), {
      target: { value: "11900000000" },
    });
    enviar();

    await waitFor(() => expect(createCustomer).toHaveBeenCalledOnce());
    expect(vi.mocked(createCustomer).mock.calls[0][0]).toMatchObject({
      document: CNPJ_VALIDO_DIGITOS,
      phone: "11900000000",
    });
  });

  it("barra documento incompleto ANTES de chamar a API, no próprio campo", async () => {
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields("123456");
    enviar();

    const campo = screen.getByLabelText("DOCUMENTO");
    await waitFor(() => expect(campo).toHaveAccessibleDescription(/Documento incompleto/));
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(createCustomer).not.toHaveBeenCalled();
  });

  it("recusa dígito verificador errado, igual a OC63 faria", async () => {
    // 14 dígitos, formato perfeito, verificador inválido: era exatamente o caso
    // que passava pela tela e tomava 422 do backend.
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields("00.000.000/0001-90");
    enviar();

    const campo = screen.getByLabelText("DOCUMENTO");
    await waitFor(() => expect(campo).toHaveAccessibleDescription("Informe um CNPJ válido."));
    expect(createCustomer).not.toHaveBeenCalled();
  });

  it("recusa telefone com DDD zerado dizendo o que está errado", async () => {
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("TELEFONE (OPCIONAL)"), {
      target: { value: "0130000000" },
    });
    enviar();

    await waitFor(() =>
      expect(screen.getByLabelText("TELEFONE (OPCIONAL)")).toHaveAccessibleDescription(
        "O DDD não pode começar com zero.",
      ),
    );
    expect(createCustomer).not.toHaveBeenCalled();
  });

  it("leva o foco para o primeiro campo errado, em vez de só pintar a tela", async () => {
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields("123456");
    enviar();

    await waitFor(() => expect(screen.getByLabelText("DOCUMENTO")).toHaveFocus());
  });

  it("depois do primeiro envio o campo se corrige enquanto se digita", async () => {
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields("123456");
    enviar();

    const campo = screen.getByLabelText("DOCUMENTO");
    await waitFor(() => expect(campo).toHaveAttribute("aria-invalid", "true"));

    fireEvent.change(campo, { target: { value: CNPJ_VALIDO } });
    await waitFor(() => expect(campo).not.toHaveAttribute("aria-invalid"));
  });

  it("não acusa erro antes do primeiro envio, com a pessoa ainda digitando", () => {
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    const campo = screen.getByLabelText("DOCUMENTO");

    fireEvent.change(campo, { target: { value: "123" } });

    expect(campo).not.toHaveAttribute("aria-invalid");
  });

  it("explica o formato do documento numa dica, sem ocupar espaço fixo", () => {
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);

    const gatilho = screen.getByRole("button", { name: "Sobre documento" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    // teclado, não só mouse: é o caso que um `title` nativo não atende
    fireEvent.focus(gatilho);
    expect(screen.getByRole("tooltip")).toHaveTextContent(/CPF ou CNPJ/);

    fireEvent.blur(gatilho);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("mostra a mensagem mapeada quando o documento já existe", async () => {
    vi.mocked(createCustomer).mockRejectedValue(
      new ApiError("CUSTOMER_DOCUMENT_ALREADY_EXISTS", "conflito"),
    );

    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    enviar();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Já existe um cliente cadastrado com este documento.",
    );
  });

  it("pousa o 422 do backend no campo que ele apontou", async () => {
    // Nenhuma regra nova do lado da tela: o backend pode recusar por motivo que
    // o frontend não conhece, e mesmo aí a pessoa precisa saber QUAL campo.
    vi.mocked(createCustomer).mockRejectedValue(
      new ApiError("VALIDATION_ERROR", "Os dados informados são inválidos.", [
        { field: "address", message: "Value error, Endereço inválido.", type: "value_error" },
      ]),
    );

    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    enviar();

    const campo = await screen.findByLabelText("ENDEREÇO");
    await waitFor(() => expect(campo).toHaveAccessibleDescription("Endereço inválido."));
    // a faixa do topo ficaria repetindo o que o campo já diz
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("volta para a faixa geral quando o 422 não aponta campo conhecido", async () => {
    // Campo que a tela não tem não some: a faixa do topo assume e ainda NOMEIA
    // o campo, em vez de devolver "dados inválidos" e deixar a pessoa caçando.
    vi.mocked(createCustomer).mockRejectedValue(
      new ApiError("VALIDATION_ERROR", "Os dados informados são inválidos.", [
        { field: "campo_desconhecido", message: "Value error, Está errado.", type: "value_error" },
      ]),
    );

    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    enviar();

    const faixa = await screen.findByRole("alert");
    expect(faixa).toHaveTextContent("campo_desconhecido");
    // o prefixo que o Pydantic acrescenta não chega ao usuário
    expect(faixa).not.toHaveTextContent("Value error");
  });
});
