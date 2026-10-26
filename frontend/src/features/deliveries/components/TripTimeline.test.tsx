import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getTripTimeline } from "../api/timelineApi";
import { TripTimeline } from "./TripTimeline";

vi.mock("../api/timelineApi");
const item = {
  id: "event1", source: "TRIP_CANCELLATION", kind: "TRIP_CANCELED",
  entity_id: "trip1", occurred_at: "2026-10-22T10:00:00Z",
  actor_id: null, status_before: null, status_after: null,
};

describe("TripTimeline", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getTripTimeline).mockResolvedValue({
      items: [item], page: 1, page_size: 20, total: 1,
    });
  });

  it("mostra eventos reais OC94 sem motivos e sem dados pessoais", async () => {
    render(<TripTimeline tripId="trip1" />);
    expect(await screen.findByText("Viagem cancelada")).toBeInTheDocument();
    expect(screen.getByText(/Não são mostradas descrições livres/)).toBeInTheDocument();
    expect(getTripTimeline).toHaveBeenCalledWith("trip1", 1);
  });

  it("solicita nova pagina ao servidor sem misturar outros registros", async () => {
    vi.mocked(getTripTimeline).mockResolvedValue({
      items: [item], page: 1, page_size: 20, total: 30,
    });
    render(<TripTimeline tripId="trip1" />);
    await screen.findByText("Viagem cancelada");
    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(getTripTimeline).toHaveBeenCalledWith("trip1", 2));
  });

  it("apresenta erro explicito quando API falha", async () => {
    vi.mocked(getTripTimeline).mockRejectedValue(new Error("sem rede"));
    render(<TripTimeline tripId="trip1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Não foi possível/);
    expect(screen.queryByText("Nenhum evento encontrado")).not.toBeInTheDocument();
  });
});

it("traduz estados de viagem e entrega sem confundir os recursos", async () => {
  vi.mocked(getTripTimeline).mockResolvedValue({page: 1, page_size: 20, total: 2, items: [
    {...item, id: "trip-event", source: "STATUS_HISTORY", kind: "STATUS_CHANGED", entity_id: "trip1", status_before: "SCHEDULED", status_after: "IN_ROUTE"},
    {...item, id: "delivery-event", source: "STATUS_HISTORY", kind: "STATUS_CHANGED", entity_id: "delivery1", status_before: "IN_DELIVERY", status_after: "DELIVERED"},
  ]});
  render(<TripTimeline tripId="trip1" />);
  expect(await screen.findByText("Mudança de situação: Agendada → Em rota")).toBeInTheDocument();
  expect(screen.getByText("Mudança de situação: Em entrega → Entregue")).toBeInTheDocument();
  expect(screen.queryByText(/SCHEDULED|IN_DELIVERY/)).not.toBeInTheDocument();
});
