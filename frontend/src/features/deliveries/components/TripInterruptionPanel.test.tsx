import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  changeTripInterruption,
  listTripInterruptions,
} from "../api/tripInterruptionApi";
import type { Trip } from "../types";
import { TripInterruptionPanel } from "./TripInterruptionPanel";

vi.mock("../api/tripInterruptionApi");

function trip(status: Trip["status"]): Trip {
  return {
    id: "trip-one",
    loadPlanId: "plan-one",
    driverId: "driver-one",
    status,
    startedAt: status === "SCHEDULED" ? null : "2026-10-21T17:00:00Z",
    finishedAt: null,
    deliveries: [],
  };
}

describe("TripInterruptionPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listTripInterruptions).mockResolvedValue([]);
  });

  it("nao permite pausar uma viagem ainda agendada", async () => {
    render(<TripInterruptionPanel trip={trip("SCHEDULED")} onChanged={vi.fn()} />);
    await waitFor(() => expect(listTripInterruptions).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Interromper viagem" })).not.toBeInTheDocument();
  });

  it("exige motivo e confirmacao antes de interromper", async () => {
    vi.mocked(changeTripInterruption).mockResolvedValue({
      id: "event-1",
      trip_id: "trip-one",
      actor_id: "manager-one",
      idempotency_key: "key-one",
      action: "INTERRUPTED",
      reason: "Falha mecanica do veiculo",
      created_at: "2026-10-21T17:10:00Z",
      trip_status: "INTERRUPTED",
    });
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(<TripInterruptionPanel trip={trip("IN_ROUTE")} onChanged={refresh} />);
    fireEvent.click(screen.getByRole("button", { name: "Interromper viagem" }));
    const confirm = screen.getByRole("button", { name: "Confirmar interrupção" });
    expect(confirm).toBeDisabled();
    expect(changeTripInterruption).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole("textbox", { name: /Motivo obrigatório/ }), {
      target: { value: "Falha mecanica do veiculo" },
    });
    fireEvent.click(confirm);
    await waitFor(() => expect(changeTripInterruption).toHaveBeenCalled());
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  });

  it("confirma a retomada com motivo sem antecipar nova entrega", async () => {
    const onChanged = vi.fn().mockResolvedValue(undefined);
    vi.mocked(changeTripInterruption).mockResolvedValue({
      id: "event-2",
      trip_id: "trip-one",
      actor_id: "manager-one",
      idempotency_key: "key-two",
      action: "RESUMED",
      reason: "Veículo reparado e liberado",
      created_at: "2026-10-21T19:00:00Z",
      trip_status: "IN_ROUTE",
    });
    render(<TripInterruptionPanel trip={trip("INTERRUPTED")} onChanged={onChanged} />);
    fireEvent.click(screen.getByRole("button", { name: "Retomar viagem" }));
    fireEvent.change(screen.getByRole("textbox", { name: /Motivo obrigatório/ }), {
      target: { value: "Veículo reparado e liberado" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar retomada" }));
    await waitFor(() => expect(changeTripInterruption).toHaveBeenCalledWith(
      "trip-one", "RESUMED", "Veículo reparado e liberado", expect.any(String),
    ));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
  });

  it("oferece retomada apenas quando a viagem esta interrompida", () => {
    render(<TripInterruptionPanel trip={trip("INTERRUPTED")} onChanged={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Retomar viagem" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Interromper viagem" })).not.toBeInTheDocument();
  });
});
