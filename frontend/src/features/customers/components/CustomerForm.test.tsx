import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { createCustomer } from "../api/customersApi";
import type { Customer } from "../types";
import { CustomerForm } from "./CustomerForm";
import { mapCustomerErrorToMessage } from "./customersErrorMessages";

vi.mock("../api/customersApi");

const CUSTOMER: Customer = {
  id: "c1",
  name: "Distribuidora Aurora",
  document: "12.345.678/0001-90",
  phone: null,
  address: "Rua das Palmeiras, 120",
  city: "Campinas",
  state: "SP",
  notes: null,
  createdAt: "2026-08-01T12:00:00Z",
};

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("NOME OU RAZÃO SOCIAL"), { target: { value: "Mercado Central" } });
  fireEvent.change(screen.getByLabelText("DOCUMENTO"), { target: { value: "99.888.777/0001-66" } });
  fireEvent.change(screen.getByLabelText("ENDEREÇO"), { target: { value: "Av. Brasil, 500" } });
  fireEvent.change(screen.getByLabelText("CIDADE"), { target: { value: "Sorocaba" } });
  fireEvent.change(screen.getByLabelText("UF"), { target: { value: "sp" } });
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
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar cliente" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(createCustomer).toHaveBeenCalledWith({
      name: "Mercado Central",
      // Só os dígitos: com pontuação, o mesmo CNPJ entraria duas vezes,
      // porque a unicidade no backend compara a string crua.
      document: "99888777000166",
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

  it("barra documento incompleto ANTES de chamar a API", async () => {
    // O backend aceita texto livre em `document`: sem esta barreira, um CPF
    // pela metade seria gravado sem reclamação nenhuma.
    render(<CustomerForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("NOME OU RAZÃO SOCIAL"), {
      target: { value: "Mercado" },
    });
    fireEvent.change(screen.getByLabelText("DOCUMENTO"), { target: { value: "123456" } });
    fireEvent.change(screen.getByLabelText("ENDEREÇO"), { target: { value: "Rua A" } });
    fireEvent.change(screen.getByLabelText("CIDADE"), { target: { value: "Sorocaba" } });
    fireEvent.change(screen.getByLabelText("UF"), { target: { value: "SP" } });

    fireEvent.click(screen.getByRole("button", { name: "Cadastrar cliente" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Documento incompleto/);
    expect(createCustomer).not.toHaveBeenCalled();
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
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar cliente" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Já existe um cliente cadastrado com este documento.",
    );
  });
});
