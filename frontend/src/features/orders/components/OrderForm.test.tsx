import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import type { Customer } from "../../customers/types";
import type { Product } from "../../products/types";
import { changeOrderStatus, createOrder, updateOrder } from "../api/ordersApi";
import type { Order } from "../types";
import { OrderForm } from "./OrderForm";
import { mapOrderErrorToMessage } from "./ordersErrorMessages";

vi.mock("../api/ordersApi");

const CUSTOMERS: Customer[] = [
  {
    id: "c1",
    name: "Distribuidora Aurora",
    document: "1",
    phone: null,
    address: "Rua A",
    city: "Campinas",
    state: "SP",
    notes: null,
    createdAt: "2026-08-01T00:00:00Z",
  },
];

const PRODUCTS: Product[] = [
  {
    id: "p1",
    code: "CX-100",
    name: "Caixa média",
    description: null,
    widthCm: 40,
    heightCm: 30,
    lengthCm: 60,
    weightKg: 12.5,
    fragile: false,
    stackable: true,
    rotationAllowed: true,
    createdAt: "2026-08-01T00:00:00Z",
  },
  {
    id: "p2",
    code: "PL-200",
    name: "Pallet padrão",
    description: null,
    widthCm: 100,
    heightCm: 120,
    lengthCm: 120,
    weightKg: 25,
    fragile: false,
    stackable: true,
    rotationAllowed: true,
    createdAt: "2026-08-01T00:00:00Z",
  },
];

const ORDER: Order = {
  id: "o1",
  customerId: "c1",
  status: "DRAFT",
  priority: "NORMAL",
  deliveryAddress: "Av. Brasil, 500",
  expectedDeliveryAt: null,
  createdAt: "2026-08-01T00:00:00Z",
  items: [{ id: "i1", orderId: "o1", productId: "p1", quantity: 4, deliverySequence: 1 }],
};

function renderForm(order?: Order) {
  return render(
    <OrderForm
      order={order}
      customers={CUSTOMERS}
      products={PRODUCTS}
      onSaved={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
}

describe("mapOrderErrorToMessage", () => {
  it("traduz itens presos a um plano de carga", () => {
    expect(mapOrderErrorToMessage(new ApiError("ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN", "x"))).toBe(
      "Os itens deste pedido já estão em um plano de carga e não podem ser alterados.",
    );
  });

  it("distingue cliente inexistente de produto inexistente", () => {
    expect(mapOrderErrorToMessage(new ApiError("ORDER_CUSTOMER_NOT_FOUND", "x"))).toContain("cliente");
    expect(mapOrderErrorToMessage(new ApiError("ORDER_PRODUCT_NOT_FOUND", "x"))).toContain("produtos");
  });
});

describe("OrderForm", () => {
  beforeEach(() => {
    vi.mocked(createOrder).mockReset();
    vi.mocked(updateOrder).mockReset();
    vi.mocked(changeOrderStatus).mockReset();
  });

  it("nasce com um item, porque o backend exige no mínimo um", () => {
    renderForm();

    expect(screen.getByLabelText("PRODUTO 1")).toBeInTheDocument();
    expect(screen.queryByLabelText("PRODUTO 2")).not.toBeInTheDocument();
  });

  it("impede remover o último item", () => {
    renderForm();

    expect(screen.getByRole("button", { name: "Remover" })).toBeDisabled();
  });

  it("adiciona e remove itens, liberando o botão quando há mais de um", () => {
    renderForm();

    fireEvent.click(screen.getByRole("button", { name: "+ Adicionar item" }));
    expect(screen.getByLabelText("PRODUTO 2")).toBeInTheDocument();

    const removeButtons = screen.getAllByRole("button", { name: "Remover" });
    expect(removeButtons[0]).toBeEnabled();

    fireEvent.click(removeButtons[1]);
    expect(screen.queryByLabelText("PRODUTO 2")).not.toBeInTheDocument();
  });

  it("remove o item certo, não o último da lista", () => {
    renderForm();

    fireEvent.click(screen.getByRole("button", { name: "+ Adicionar item" }));
    fireEvent.change(screen.getByLabelText("PRODUTO 1"), { target: { value: "p1" } });
    fireEvent.change(screen.getByLabelText("PRODUTO 2"), { target: { value: "p2" } });

    // remove o primeiro; o que sobra tem que ser o p2, renumerado para PRODUTO 1
    fireEvent.click(screen.getAllByRole("button", { name: "Remover" })[0]);

    expect(screen.getByLabelText("PRODUTO 1")).toHaveValue("p2");
  });

  it("manda TODOS os itens com a mesma sequência de entrega", async () => {
    // Regressão: a sequência era um campo por item e cada item novo nascia com
    // um número diferente. O backend exige uma só por pedido
    // (`_validate_single_delivery_sequence`), então salvar dois itens devolvia
    // 422 "Os dados informados são inválidos", sem dizer o motivo.
    vi.mocked(createOrder).mockResolvedValue(ORDER);

    renderForm();
    fireEvent.change(screen.getByLabelText("CLIENTE"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("ENDEREÇO DE ENTREGA"), {
      target: { value: "Av. Brasil, 500" },
    });
    fireEvent.change(screen.getByLabelText("SEQ. DE ENTREGA"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("PRODUTO 1"), { target: { value: "p1" } });

    fireEvent.click(screen.getByRole("button", { name: "+ Adicionar item" }));
    fireEvent.change(screen.getByLabelText("PRODUTO 2"), { target: { value: "p2" } });

    fireEvent.click(screen.getByRole("button", { name: "Cadastrar pedido" }));

    await waitFor(() => expect(createOrder).toHaveBeenCalled());
    const enviados = vi.mocked(createOrder).mock.calls[0][0].items;
    expect(enviados).toHaveLength(2);
    expect(new Set(enviados.map((item) => item.deliverySequence))).toEqual(new Set([3]));
  });

  it("não oferece sequência por item, que era o convite para divergir", () => {
    renderForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Adicionar item" }));

    expect(screen.getByLabelText("SEQ. DE ENTREGA")).toBeInTheDocument();
    expect(screen.queryByLabelText("SEQ. ENTREGA")).not.toBeInTheDocument();
  });

  it("envia os itens em camelCase e sem previsão quando o campo fica vazio", async () => {
    vi.mocked(createOrder).mockResolvedValue(ORDER);

    renderForm();
    fireEvent.change(screen.getByLabelText("CLIENTE"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("ENDEREÇO DE ENTREGA"), {
      target: { value: "Av. Brasil, 500" },
    });
    fireEvent.change(screen.getByLabelText("PRODUTO 1"), { target: { value: "p1" } });
    fireEvent.change(screen.getByLabelText("QTD."), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar pedido" }));

    await waitFor(() => expect(createOrder).toHaveBeenCalled());
    expect(createOrder).toHaveBeenCalledWith({
      customerId: "c1",
      priority: "NORMAL",
      deliveryAddress: "Av. Brasil, 500",
      expectedDeliveryAt: null,
      items: [{ productId: "p1", quantity: 4, deliverySequence: 1 }],
    });
  });

  it("manda a previsão de entrega com fuso, que o backend exige", async () => {
    vi.mocked(createOrder).mockResolvedValue(ORDER);

    renderForm();
    fireEvent.change(screen.getByLabelText("CLIENTE"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("ENDEREÇO DE ENTREGA"), { target: { value: "Av. Brasil, 500" } });
    fireEvent.change(screen.getByLabelText("PRODUTO 1"), { target: { value: "p1" } });
    fireEvent.change(screen.getByLabelText("PREVISÃO (OPCIONAL)"), {
      target: { value: "2026-08-10T14:30" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar pedido" }));

    await waitFor(() => expect(createOrder).toHaveBeenCalled());
    expect(vi.mocked(createOrder).mock.calls[0][0].expectedDeliveryAt).toMatch(/Z$/);
  });

  it("não expõe a situação na criação", () => {
    renderForm();

    expect(screen.queryByLabelText("SITUAÇÃO")).not.toBeInTheDocument();
  });

  it("oferece só as transições manuais permitidas a partir da situação atual", () => {
    renderForm(ORDER); // DRAFT -> READY | CANCELED

    const options = [...screen.getByLabelText("SITUAÇÃO").querySelectorAll("option")].map((o) => o.value);

    expect(options).toEqual(["DRAFT", "READY", "CANCELED"]);
    expect(options).not.toContain("PLANNED");
    expect(options).not.toContain("DELIVERED");
  });

  it("deixa a situação só de leitura quando não há transição manual", () => {
    renderForm({ ...ORDER, status: "PLANNED" });

    const field = screen.getByLabelText("SITUAÇÃO");

    expect(field).toHaveAttribute("readonly");
    expect(field).toHaveValue("Planejado");
  });

  it("manda a situação pelo endpoint dedicado, nunca no PATCH genérico", async () => {
    vi.mocked(updateOrder).mockResolvedValue(ORDER);
    vi.mocked(changeOrderStatus).mockResolvedValue({ ...ORDER, status: "READY" });

    renderForm(ORDER);
    fireEvent.change(screen.getByLabelText("SITUAÇÃO"), { target: { value: "READY" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(changeOrderStatus).toHaveBeenCalledWith(ORDER.id, "READY"));
    // OrderUpdate usa extra="forbid": mandar status ali volta 422
    expect(vi.mocked(updateOrder).mock.calls[0][1]).not.toHaveProperty("status");
  });

  it("não chama o endpoint de situação quando ela não mudou", async () => {
    vi.mocked(updateOrder).mockResolvedValue(ORDER);

    renderForm(ORDER);
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(updateOrder).toHaveBeenCalled());
    expect(changeOrderStatus).not.toHaveBeenCalled();
  });

  it("traduz a recusa de transição do backend", async () => {
    vi.mocked(updateOrder).mockResolvedValue(ORDER);
    vi.mocked(changeOrderStatus).mockRejectedValue(
      new ApiError("ORDER_STATUS_TRANSITION_NOT_ALLOWED", "x"),
    );

    renderForm(ORDER);
    fireEvent.change(screen.getByLabelText("SITUAÇÃO"), { target: { value: "CANCELED" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Esta mudança de situação não é permitida",
    );
  });

  it("mostra a mensagem mapeada quando o backend recusa", async () => {
    vi.mocked(createOrder).mockRejectedValue(new ApiError("ORDER_CUSTOMER_NOT_FOUND", "x"));

    renderForm();
    fireEvent.change(screen.getByLabelText("CLIENTE"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("ENDEREÇO DE ENTREGA"), { target: { value: "Av. Brasil, 500" } });
    fireEvent.change(screen.getByLabelText("PRODUTO 1"), { target: { value: "p1" } });
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar pedido" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("O cliente selecionado não existe mais.");
  });
});
