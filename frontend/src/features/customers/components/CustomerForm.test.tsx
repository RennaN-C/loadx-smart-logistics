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
      document: "99.888.777/0001-66",
      phone: null,
      address: "Av. Brasil, 500",
      city: "Sorocaba",
      state: "SP",
      notes: null,
    });
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
