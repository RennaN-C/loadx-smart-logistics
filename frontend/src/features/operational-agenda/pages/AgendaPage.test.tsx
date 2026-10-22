import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchAgenda } from "../api/agendaApi";
import { AgendaPage } from "./AgendaPage";

vi.mock("../api/agendaApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/agendaApi")>();
  return { ...actual, fetchAgenda: vi.fn() };
});
const event = {
  kind: "TRIP_CREATED" as const,
  resource_id: "event1", trip_id: "trip1",
  occurred_at: "2026-10-22T10:00:00Z",
  truck_id: "truck1", driver_id: "driver1",
};

function renderAgenda() {
  return render(<MemoryRouter><AgendaPage /></MemoryRouter>);
}

describe("AgendaPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchAgenda).mockResolvedValue({
      start: "2026-10-22T00:00:00Z", end: "2026-10-23T00:00:00Z",
      total: 1, items: [event],
    });
  });

  it("exibe fatos reais com navegação para viagem e sem ETA inventado", async () => {
    renderAgenda();
    expect(await screen.findByText("Viagem criada")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir viagem" })).toHaveAttribute("href", "/trips/trip1");
    expect(screen.getByText(/não de horários previstos/)).toBeInTheDocument();
  });

  it("filtra eventos no servidor mantendo janela de até sete dias", async () => {
    renderAgenda();
    await screen.findByText("Viagem criada");
    fireEvent.change(screen.getByLabelText("Tipo de evento"), {
      target: { value: "TRIP_CANCELED" },
    });
    await waitFor(() => expect(fetchAgenda).toHaveBeenLastCalledWith(
      expect.objectContaining({ kind: "TRIP_CANCELED" }),
    ));
  });

  it("preserva uma data válida ao limpar o campo e mantém a navegação", async () => {
    renderAgenda();
    await screen.findByText("Viagem criada");
    const date = screen.getByLabelText("Data inicial") as HTMLInputElement;
    const initial = date.value;
    fireEvent.change(date, { target: { value: "" } });
    expect(date).toHaveValue(initial);
    fireEvent.click(screen.getByRole("button", { name: "Próximo" }));
    await waitFor(() => expect(date.value).not.toBe(initial));
    const last = vi.mocked(fetchAgenda).mock.calls.at(-1)?.[0];
    expect(last).toBeDefined();
    expect(Number.isFinite(Date.parse(last!.start))).toBe(true);
    expect(Date.parse(last!.end) - Date.parse(last!.start)).toBe(7 * 86400000);
  });

  it("diferencia ausencia de eventos e erro de rede", async () => {
    vi.mocked(fetchAgenda).mockResolvedValue({
      start: "2026-10-22T00:00:00Z", end: "2026-10-23T00:00:00Z",
      total: 0, items: [],
    });
    renderAgenda();
    expect(await screen.findByText(/Nenhuma atividade registrada/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
