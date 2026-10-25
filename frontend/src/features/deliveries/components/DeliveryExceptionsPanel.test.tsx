import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  listDeliveryExceptions,
  registerDeliveryException,
  type DeliveryException,
} from "../api/deliveryExceptionsApi";
import type { Delivery } from "../types";
import { DeliveryExceptionsPanel } from "./DeliveryExceptionsPanel";

vi.mock("../api/deliveryExceptionsApi");

const delivery: Delivery = {
  id: "delivery-1",
  tripId: "trip-1",
  orderId: "order-1",
  sequence: 1,
  status: "IN_DELIVERY",
  deliveredAt: null,
};

const occurrence: DeliveryException = {
  id: "event-1",
  delivery_id: delivery.id,
  trip_id: delivery.tripId,
  code: "CUSTOMER_ABSENT",
  reason: "Cliente ausente no horario previsto",
  actor_id: "actor-1",
  idempotency_key: "request-1",
  created_at: "2026-10-21T12:00:00Z",
  scheduled_for: null,
};

describe("DeliveryExceptionsPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("crypto", { randomUUID: () => "request-1" });
    vi.mocked(listDeliveryExceptions).mockResolvedValue([]);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("só consulta o histórico quando o operador abre o painel", async () => {
    render(<DeliveryExceptionsPanel deliveries={[delivery]} canOperate />);
    expect(listDeliveryExceptions).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Consultar ou registrar ocorrência" }));
    await waitFor(() => expect(listDeliveryExceptions).toHaveBeenCalledWith(delivery.id));
    expect(await screen.findByText(/Não há ocorrências registradas/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar no histórico" })).toBeDisabled();
  });

  it("registra uma falha sem modificar a entrega diretamente", async () => {
    vi.mocked(listDeliveryExceptions)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([occurrence]);
    vi.mocked(registerDeliveryException).mockResolvedValue(occurrence);

    render(<DeliveryExceptionsPanel deliveries={[delivery]} canOperate />);
    fireEvent.click(screen.getByRole("button", { name: "Consultar ou registrar ocorrência" }));
    await screen.findByText(/Não há ocorrências registradas/);
    fireEvent.change(screen.getByLabelText("Motivo (mínimo de 10 caracteres)"), {
      target: { value: occurrence.reason },
    });
    fireEvent.click(screen.getByRole("button", { name: "Registrar no histórico" }));

    await waitFor(() => expect(registerDeliveryException).toHaveBeenCalledWith(
      delivery.id,
      {
        code: "CUSTOMER_ABSENT",
        reason: occurrence.reason,
        idempotency_key: "request-1",
      },
    ));
    expect(await screen.findByText(occurrence.reason)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Reagendar tentativa" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Retomar tentativa" })).toBeInTheDocument();
  });

  it("exibe estados legíveis e ignora respostas atrasadas de outra entrega", async () => {
    let resolveFirst!: (value: DeliveryException[]) => void;
    vi.mocked(listDeliveryExceptions)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }))
      .mockResolvedValueOnce([occurrence]);
    const other = { ...delivery, id: "delivery-2", sequence: 2, status: "DELIVERED" as const };
    render(<DeliveryExceptionsPanel deliveries={[delivery, other]} canOperate />);
    fireEvent.click(screen.getByRole("button", { name: "Consultar ou registrar ocorrência" }));
    const picker = screen.getByLabelText("Entrega");
    expect(screen.getByRole("option", { name: "Parada 1 — Em entrega" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Parada 2 — Entregue" })).toBeInTheDocument();
    fireEvent.change(picker, { target: { value: other.id } });
    expect(await screen.findByText(occurrence.reason)).toBeInTheDocument();
    resolveFirst([]);
    await waitFor(() => expect(screen.getByText(occurrence.reason)).toBeInTheDocument());
  });

  it("não permite registrar ocorrência em uma entrega cancelada", async () => {
    render(<DeliveryExceptionsPanel deliveries={[{ ...delivery, status: "CANCELED" }]} canOperate />);
    fireEvent.click(screen.getByRole("button", { name: "Consultar ou registrar ocorrência" }));
    await screen.findByText(/Não há ocorrências registradas/);
    expect(screen.queryByRole("button", { name: "Registrar no histórico" })).not.toBeInTheDocument();
  });

  it("respeita a permissão apenas de leitura do histórico", async () => {
    render(<DeliveryExceptionsPanel deliveries={[delivery]} canOperate={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Consultar ou registrar ocorrência" }));
    await screen.findByText(/Não há ocorrências registradas/);
    expect(screen.queryByRole("button", { name: "Registrar no histórico" })).not.toBeInTheDocument();
  });

  it("não permite registrar nova ocorrência em entrega concluída", async () => {
    render(
      <DeliveryExceptionsPanel
        deliveries={[{ ...delivery, status: "DELIVERED", deliveredAt: "2026-10-21T12:30:00Z" }]}
        canOperate
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Consultar ou registrar ocorrência" }));
    await screen.findByText(/Não há ocorrências registradas/);
    expect(screen.queryByRole("button", { name: "Registrar no histórico" })).not.toBeInTheDocument();
  });
});
