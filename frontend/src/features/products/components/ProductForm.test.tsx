import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { createProduct, updateProduct } from "../api/productsApi";
import type { Product } from "../types";
import { ProductForm } from "./ProductForm";
import { mapProductErrorToMessage } from "./productsErrorMessages";

vi.mock("../api/productsApi");

const PRODUCT: Product = {
  id: "33333333-3333-3333-3333-333333333333",
  code: "CX-100",
  name: "Caixa média",
  description: "Papelão reforçado",
  widthCm: 40,
  heightCm: 30,
  lengthCm: 60,
  weightKg: 12.5,
  fragile: false,
  stackable: true,
  rotationAllowed: true,
  createdAt: "2026-08-01T12:00:00Z",
};

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("CÓDIGO"), { target: { value: "pl-200" } });
  fireEvent.change(screen.getByLabelText("NOME"), { target: { value: "Pallet padrão" } });
  fireEvent.change(screen.getByLabelText("LARGURA (CM)"), { target: { value: "100" } });
  fireEvent.change(screen.getByLabelText("ALTURA (CM)"), { target: { value: "120" } });
  fireEvent.change(screen.getByLabelText("COMPRIMENTO (CM)"), { target: { value: "120" } });
  // ponto, não vírgula: input[type=number] descarta o valor com vírgula e o
  // campo required passa a bloquear o envio
  fireEvent.change(screen.getByLabelText("PESO (KG)"), { target: { value: "25.5" } });
}

describe("mapProductErrorToMessage", () => {
  it("traduz PRODUCT_CODE_ALREADY_EXISTS", () => {
    expect(mapProductErrorToMessage(new ApiError("PRODUCT_CODE_ALREADY_EXISTS", "conflito"))).toBe(
      "Já existe um produto cadastrado com este código.",
    );
  });

  it("usa a mensagem do backend para qualquer outro código", () => {
    expect(mapProductErrorToMessage(new ApiError("VALIDATION_ERROR", "Dados inválidos."))).toBe(
      "Dados inválidos.",
    );
  });
});

describe("ProductForm", () => {
  beforeEach(() => {
    vi.mocked(createProduct).mockReset();
    vi.mocked(updateProduct).mockReset();
  });

  it("normaliza o código em maiúsculas e envia o payload em camelCase", async () => {
    vi.mocked(createProduct).mockResolvedValue(PRODUCT);
    const onSaved = vi.fn();

    render(<ProductForm onSaved={onSaved} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar produto" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(createProduct).toHaveBeenCalledWith({
      code: "PL-200",
      name: "Pallet padrão",
      description: null,
      widthCm: 100,
      heightCm: 120,
      lengthCm: 120,
      weightKg: 25.5,
      fragile: false,
      stackable: true,
      rotationAllowed: true,
    });
  });

  it("envia description nula quando o campo fica em branco", async () => {
    vi.mocked(createProduct).mockResolvedValue(PRODUCT);

    render(<ProductForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("DESCRIÇÃO (OPCIONAL)"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar produto" }));

    await waitFor(() => expect(createProduct).toHaveBeenCalled());
    expect(vi.mocked(createProduct).mock.calls[0][0].description).toBeNull();
  });

  it("nasce com os padrões do backend: empilhável e com rotação, não frágil", () => {
    render(<ProductForm onSaved={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByLabelText(/Frágil/)).not.toBeChecked();
    expect(screen.getByLabelText(/Empilhável/)).toBeChecked();
    expect(screen.getByLabelText(/Rotação permitida/)).toBeChecked();
  });

  it("calcula o volume unitário conforme as medidas digitadas", () => {
    render(<ProductForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();

    // 1,00 m x 1,20 m x 1,20 m = 1,440 m³
    expect(screen.getByText("1,440 m³")).toBeInTheDocument();
  });

  it("mostra a mensagem mapeada quando o código já existe", async () => {
    vi.mocked(createProduct).mockRejectedValue(new ApiError("PRODUCT_CODE_ALREADY_EXISTS", "conflito"));

    render(<ProductForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar produto" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Já existe um produto cadastrado com este código.",
    );
  });

  it("envia as flags alteradas na edição", async () => {
    vi.mocked(updateProduct).mockResolvedValue({ ...PRODUCT, fragile: true });
    const onSaved = vi.fn();

    render(<ProductForm product={PRODUCT} onSaved={onSaved} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByLabelText(/Frágil/));
    fireEvent.click(screen.getByLabelText(/Empilhável/));
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(updateProduct).toHaveBeenCalledWith(
      PRODUCT.id,
      expect.objectContaining({ fragile: true, stackable: false }),
    );
  });
});
