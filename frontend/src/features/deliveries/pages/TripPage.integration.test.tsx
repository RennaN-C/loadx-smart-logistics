import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../../services/api";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import type { DeliveryStatus } from "../types";
import { TripPage } from "./TripPage";

vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), patch: vi.fn() } }));
vi.mock("../../auth/hooks/useAuth");

function deliveryDto(status: DeliveryStatus) {
  return {
    id: "dl1", trip_id: "tp1", order_id: "o1", status, sequence: 1,
    delivered_at: status === "DELIVERED" ? "2026-09-09T12:00:00Z" : null,
  };
}

function tripDto(status: DeliveryStatus) {
  return {
    id: "tp1", load_plan_id: "lp1", driver_id: "d1", status: "IN_ROUTE",
    started_at: "2026-09-09T10:00:00Z", finished_at: null,
    deliveries: [deliveryDto(status)],
  };
}

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/trips/tp1"]}>
      <Routes><Route path="/trips/:tripId" element={<TripPage />} /></Routes>
    </MemoryRouter>,
  );
}

describe("TripPage com adapter e hook reais", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useAuth).mockReturnValue({
      status: "authenticated",
      user: {
        id: "u1", name: "Motorista de teste", email: "driver@example.test",
        role: "DRIVER", active: true, createdAt: "2026-09-09T00:00:00Z",
      },
      login: vi.fn(), logout: vi.fn(),
    });
    vi.mocked(api.get).mockResolvedValueOnce({ data: tripDto("PENDING") });
  });

  it("percorre PENDING -> IN_DELIVERY -> DELIVERED e só atualiza a tela após cada GET", async () => {
    let finishReload!: (value: { data: ReturnType<typeof tripDto> }) => void;
    vi.mocked(api.patch)
      .mockResolvedValueOnce({ data: deliveryDto("IN_DELIVERY") })
      .mockResolvedValueOnce({ data: deliveryDto("DELIVERED") });
    vi.mocked(api.get)
      .mockImplementationOnce(() => new Promise((resolve) => { finishReload = resolve; }))
      .mockResolvedValueOnce({ data: tripDto("DELIVERED") });

    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Iniciar entrega" }));

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
    expect(screen.getByRole("button", { name: "Iniciar entrega" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Confirmar entrega" })).not.toBeInTheDocument();
    finishReload({ data: tripDto("IN_DELIVERY") });

    fireEvent.click(await screen.findByRole("button", { name: "Confirmar entrega" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Finalizar viagem" })).toBeEnabled());
    expect(screen.getByText("Entregue")).toBeInTheDocument();
    expect(screen.getByText(/entregue em/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(api.patch).toHaveBeenNthCalledWith(1, "/deliveries/dl1/status", { status: "IN_DELIVERY" });
    expect(api.patch).toHaveBeenNthCalledWith(2, "/deliveries/dl1/status", { status: "DELIVERED" });
    expect(api.get).toHaveBeenCalledTimes(3);
    expect(api.get).toHaveBeenLastCalledWith("/trips/tp1");
  });

  it("mostra erro de domínio do PATCH e preserva a viagem exibida", async () => {
    vi.mocked(api.patch).mockRejectedValue(new ApiError("DELIVERY_TRIP_NOT_IN_ROUTE", "x"));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Iniciar entrega" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("A viagem precisa estar em rota");
    expect(screen.getByRole("button", { name: "Iniciar entrega" })).toBeEnabled();
    expect(api.get).toHaveBeenCalledTimes(1);
  });

  it("trata falha do GET após PATCH e mantém o último estado conhecido sem TypeError", async () => {
    vi.mocked(api.patch).mockResolvedValue({ data: deliveryDto("IN_DELIVERY") });
    vi.mocked(api.get).mockRejectedValueOnce(new ApiError("TRIP_NOT_FOUND", "x"));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Iniciar entrega" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Esta viagem não foi encontrada.");
    expect(screen.getByRole("button", { name: "Iniciar entrega" })).toBeEnabled();
    expect(api.patch).toHaveBeenCalledTimes(1);
    expect(api.get).toHaveBeenCalledTimes(2);
  });
});
