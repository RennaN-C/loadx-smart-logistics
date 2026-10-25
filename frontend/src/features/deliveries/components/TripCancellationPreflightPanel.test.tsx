import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { cancelScheduledTrip, getCancellationPreflight } from "../api/cancellationPreflightApi";
import { TripCancellationPreflightPanel } from "./TripCancellationPreflightPanel";

vi.mock("../api/cancellationPreflightApi");

describe("TripCancellationPreflightPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getCancellationPreflight).mockResolvedValue({
      trip_id: "trip-1",
      safe_for_cancellation_workflow: false,
      blocking_reasons: ["LOADING_SESSION_EXISTS"],
      next_action: "RESOLVER_BLOQUEIOS_OPERACIONAIS",
    });
  });

  it("não consulta nem cancela antes da ação explícita", () => {
    render(<TripCancellationPreflightPanel tripId="trip-1" />);
    expect(getCancellationPreflight).not.toHaveBeenCalled();
    expect(screen.getByText(/O cancelamento exige motivo/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancelar viagem" })).not.toBeInTheDocument();
  });

  it("mostra bloqueios reais sem permitir operações irreversíveis", async () => {
    render(<TripCancellationPreflightPanel tripId="trip-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Verificar bloqueios" }));
    await waitFor(() => expect(getCancellationPreflight).toHaveBeenCalledWith("trip-1"));
    expect(await screen.findByText(/Existe uma sessão de carregamento/)).toBeInTheDocument();
  });

  it("exige motivo antes da confirmação e executa apenas após clique explícito", async () => {
    vi.mocked(getCancellationPreflight).mockResolvedValue({
      trip_id: "trip-1",
      safe_for_cancellation_workflow: true,
      blocking_reasons: [],
      next_action: "PREPARAR_RECONCILIACAO_TRANSACIONAL",
    });
    render(<TripCancellationPreflightPanel tripId="trip-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Verificar bloqueios" }));
    fireEvent.click(await screen.findByRole("button", { name: "Solicitar cancelamento" }));
    const submit = screen.getByRole("button", { name: "Confirmar cancelamento" });
    expect(submit).toBeDisabled();
    expect(cancelScheduledTrip).not.toHaveBeenCalled();
  });

  it("não permite cancelar sem permissão mesmo após preflight favorável", async () => {
    vi.mocked(getCancellationPreflight).mockResolvedValue({
      trip_id: "trip-1",
      safe_for_cancellation_workflow: true,
      blocking_reasons: [],
      next_action: "PREPARAR_RECONCILIACAO_TRANSACIONAL",
    });
    render(<TripCancellationPreflightPanel tripId="trip-1" canCancel={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Verificar bloqueios" }));
    expect(await screen.findByText(/Pré-validação aprovada/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Solicitar cancelamento" })).not.toBeInTheDocument();
    expect(cancelScheduledTrip).not.toHaveBeenCalled();
  });

  it("não confunde elegibilidade preliminar com cancelamento executado", async () => {
    vi.mocked(getCancellationPreflight).mockResolvedValue({
      trip_id: "trip-1",
      safe_for_cancellation_workflow: true,
      blocking_reasons: [],
      next_action: "PREPARAR_RECONCILIACAO_TRANSACIONAL",
    });
    render(<TripCancellationPreflightPanel tripId="trip-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Verificar bloqueios" }));
    expect(await screen.findByText(/Pré-validação aprovada/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancelar viagem" })).not.toBeInTheDocument();
  });
});
