import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import type { Role } from "../../auth/types";
import { useAuth } from "../../auth/hooks/useAuth";
import { changeDeliveryStatus, changeTripStatus, getTrip } from "../api/tripsApi";
import type { Trip } from "../types";
import { TripPage } from "./TripPage";

vi.mock("../api/tripsApi");
vi.mock("../../auth/hooks/useAuth");

function makeTrip(overrides: Partial<Trip> = {}): Trip {
  return {
    id: "tp1",
    loadPlanId: "lp1",
    driverId: "d1",
    status: "SCHEDULED",
    startedAt: null,
    finishedAt: null,
    deliveries: [
      { id: "dl2", tripId: "tp1", orderId: "o2", status: "PENDING", sequence: 2, deliveredAt: null },
      { id: "dl1", tripId: "tp1", orderId: "o1", status: "PENDING", sequence: 1, deliveredAt: null },
    ],
    ...overrides,
  };
}

function mockRole(role: Role) {
  vi.mocked(useAuth).mockReturnValue({
    status: "authenticated",
    user: {
      id: "u1",
      name: "Ana Souza",
      email: "ana@example.test",
      role,
      active: true,
      createdAt: "2026-08-01T00:00:00Z",
    },
    login: vi.fn(),
    logout: vi.fn(),
  });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/trips/tp1"]}>
      <Routes>
        <Route path="/trips/:tripId" element={<TripPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("TripPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockRole("LOGISTICS_MANAGER");
    vi.mocked(getTrip).mockResolvedValue(makeTrip());
  });

  it("carrega a viagem pelo id da URL, já que o backend não lista viagens", async () => {
    renderPage();

    await waitFor(() => expect(getTrip).toHaveBeenCalledWith("tp1"));
    expect(await screen.findByText("Agendada")).toBeInTheDocument();
  });

  it("ordena as paradas pela sequência da rota, não pela ordem da API", async () => {
    renderPage();
    await screen.findByText("Agendada");

    const seqs = [...document.querySelectorAll(".trip-stop-seq")].map((el) => el.textContent);

    expect(seqs).toEqual(["1", "2"]);
  });

  it("só oferece a transição seguinte do ciclo, que é de mão única", async () => {
    renderPage();

    expect(await screen.findByRole("button", { name: "Iniciar viagem" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Finalizar viagem" })).not.toBeInTheDocument();
  });

  it("bloqueia entregas enquanto a viagem não entra em rota", async () => {
    renderPage();
    await screen.findByText("Agendada");

    expect(screen.getAllByRole("button", { name: "Iniciar entrega" })[0]).toBeDisabled();
    expect(screen.getByText(/só podem ser movimentadas depois/)).toBeInTheDocument();
  });

  it("libera as entregas com a viagem em rota", async () => {
    vi.mocked(getTrip).mockResolvedValue(makeTrip({ status: "IN_ROUTE", startedAt: "2026-08-09T10:00:00Z" }));
    vi.mocked(changeDeliveryStatus).mockResolvedValue(makeTrip({ status: "IN_ROUTE" }));

    renderPage();
    await screen.findByText("Em rota");

    const button = screen.getAllByRole("button", { name: "Iniciar entrega" })[0];
    expect(button).toBeEnabled();

    fireEvent.click(button);
    await waitFor(() => expect(changeDeliveryStatus).toHaveBeenCalledWith("dl1", "IN_DELIVERY"));
  });

  it("impede finalizar a viagem com entrega em aberto", async () => {
    vi.mocked(getTrip).mockResolvedValue(makeTrip({ status: "IN_ROUTE" }));

    renderPage();
    await screen.findByText("Em rota");

    expect(screen.getByRole("button", { name: "Finalizar viagem" })).toBeDisabled();
  });

  it("libera finalizar quando todas as entregas estão concluídas", async () => {
    vi.mocked(getTrip).mockResolvedValue(
      makeTrip({
        status: "IN_ROUTE",
        deliveries: [
          {
            id: "dl1",
            tripId: "tp1",
            orderId: "o1",
            status: "DELIVERED",
            sequence: 1,
            deliveredAt: "2026-08-09T12:00:00Z",
          },
        ],
      }),
    );
    vi.mocked(changeTripStatus).mockResolvedValue(makeTrip({ status: "FINISHED" }));

    renderPage();
    await screen.findByText("Em rota");

    const finish = screen.getByRole("button", { name: "Finalizar viagem" });
    expect(finish).toBeEnabled();

    fireEvent.click(finish);
    await waitFor(() => expect(changeTripStatus).toHaveBeenCalledWith("tp1", "FINISHED"));
  });

  it("motorista opera a viagem", async () => {
    mockRole("DRIVER");
    vi.mocked(getTrip).mockResolvedValue(makeTrip({ status: "IN_ROUTE" }));

    renderPage();
    await screen.findByText("Em rota");

    expect(screen.getAllByRole("button", { name: "Iniciar entrega" })[0]).toBeEnabled();
  });

  it("ADMIN acompanha mas não opera", async () => {
    mockRole("ADMIN");
    vi.mocked(getTrip).mockResolvedValue(makeTrip({ status: "IN_ROUTE" }));

    renderPage();
    await screen.findByText("Em rota");

    expect(screen.queryByRole("button", { name: "Finalizar viagem" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Iniciar entrega" })[0]).toBeDisabled();
  });

  it("não oferece ação na viagem já finalizada", async () => {
    vi.mocked(getTrip).mockResolvedValue(
      makeTrip({
        status: "FINISHED",
        finishedAt: "2026-08-09T18:00:00Z",
        deliveries: [
          {
            id: "dl1",
            tripId: "tp1",
            orderId: "o1",
            status: "DELIVERED",
            sequence: 1,
            deliveredAt: "2026-08-09T12:00:00Z",
          },
        ],
      }),
    );

    renderPage();
    await screen.findByText("Finalizada");

    // Baixar o PDF NÃO é ação sobre a viagem — continua disponível numa viagem
    // finalizada, que aliás é quando o relatório mais interessa. As asserções
    // apontam as transições, que são o que precisa sumir.
    for (const acao of ["Iniciar viagem", "Finalizar viagem", "Iniciar entrega", "Concluir entrega"]) {
      expect(screen.queryByRole("button", { name: acao })).not.toBeInTheDocument();
    }
  });

  it("oferece o relatório de viagem para quem tem permissão", async () => {
    vi.mocked(getTrip).mockResolvedValue(makeTrip({ status: "FINISHED" }));

    renderPage();
    await screen.findByText("Finalizada");

    expect(screen.getByRole("button", { name: "Relatório de viagem" })).toBeInTheDocument();
  });

  it("traduz a recusa de transição do backend", async () => {
    vi.mocked(getTrip).mockResolvedValue(makeTrip({ status: "IN_ROUTE" }));
    vi.mocked(changeDeliveryStatus).mockRejectedValue(
      new ApiError("DELIVERY_TRIP_NOT_IN_ROUTE", "x"),
    );

    renderPage();
    await screen.findByText("Em rota");

    fireEvent.click(screen.getAllByRole("button", { name: "Iniciar entrega" })[0]);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A viagem precisa estar em rota para movimentar as entregas.",
    );
  });
});
