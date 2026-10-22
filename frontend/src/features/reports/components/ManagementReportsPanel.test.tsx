import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { downloadManagementReport, fetchManagementSummary } from "../api/managementReportsApi";
import { ManagementReportsPanel } from "./ManagementReportsPanel";

vi.mock("../api/managementReportsApi");
const summary = {
  start: "2026-10-01T00:00:00Z",
  end: "2026-10-08T00:00:00Z",
  trips_created: 2,
  trips_started: 1,
  trips_finished: 0,
  deliveries_completed: 1,
  orders_with_completed_leg: 1,
  occurrences_registered: 3,
  delivery_exceptions: 2,
  trips_canceled: 0,
  interruption_events: 1,
};

describe("ManagementReportsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchManagementSummary).mockResolvedValue(summary);
    vi.mocked(downloadManagementReport).mockResolvedValue(undefined);
  });

  it("mostra indicadores do PostgreSQL sem chamar parte entregue de pedido concluido", async () => {
    render(<ManagementReportsPanel />);
    const panel = screen.getByRole("region", { name: "Relatório gerencial filtrado" });
    expect(await within(panel).findByText("Viagens criadas")).toBeInTheDocument();
    expect(within(panel).getByText("Pedidos com alguma parte entregue")).toBeInTheDocument();
    expect(within(panel).getByText(/não é necessariamente um pedido completamente entregue/)).toBeInTheDocument();
    expect(within(panel).getByText("Cancelamentos de viagem")).toBeInTheDocument();
  });

  it("CSV e PDF usam o mesmo filtro aplicado à API", async () => {
    render(<ManagementReportsPanel />);
    await screen.findByText("Viagens criadas");
    await waitFor(() => expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Exportar CSV" }));
    await waitFor(() => expect(downloadManagementReport).toHaveBeenCalledWith(
      "csv", expect.objectContaining({ start: expect.any(String), end: expect.any(String) }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Exportar PDF" }));
    await waitFor(() => expect(downloadManagementReport).toHaveBeenCalledWith(
      "pdf", expect.objectContaining({ start: expect.any(String), end: expect.any(String) }),
    ));
  });

  it("mostra erro recuperavel quando API falha, sem fingir resumo vazio", async () => {
    vi.mocked(fetchManagementSummary).mockRejectedValue(new Error("sem rede"));
    render(<ManagementReportsPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Falha ao consultar/);
    expect(screen.queryByText("Viagens criadas")).not.toBeInTheDocument();
  });
});
