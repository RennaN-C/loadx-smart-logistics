import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { preflightDistribution } from "../api/distributionsApi";
import { FleetPreflight } from "./FleetPreflight";
import type { DistributionNeed } from "../types";

vi.mock("../api/distributionsApi");
beforeEach(() => vi.resetAllMocks());
it("consulta a seleção e apresenta apenas veículos elegíveis retornados pelo servidor", async () => {
  vi.mocked(preflightDistribution).mockResolvedValue({ orderIds: ["order"], volumes: [], ineligibleTrucks: [{ truckId: "excluded", reason: "INACTIVE" }], eligibleTrucks: [{ id: "truck", plate: "DMO0A10", model: "DEMO Baú", widthCm: 240, heightCm: 260, lengthCm: 600, maxWeightKg: 10000 }] });
  render(<FleetPreflight orderIds={["order"]} />);
  expect(await screen.findByText("DMO0A10")).toBeInTheDocument();
  expect(preflightDistribution).toHaveBeenCalledWith(["order"]);
  expect(screen.getAllByRole("listitem")).toHaveLength(1);
  expect(screen.getByText(/1 veículo\(s\) excluído/)).toBeInTheDocument();
});
it("distingue indisponibilidade da consulta de ausência de frota e permite retry", async () => {
  vi.mocked(preflightDistribution).mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ orderIds: ["order"], volumes: [], eligibleTrucks: [], ineligibleTrucks: [] });
  render(<FleetPreflight orderIds={["order"]} />);
  fireEvent.click(await screen.findByRole("button", { name: "Consultar frota novamente" }));
  expect(await screen.findByText(/Nenhum caminhão elegível/)).toBeInTheDocument();
});

it("ignora resposta antiga após mudar os pedidos e invalida o resultado ao atualizar a frota", async () => {
  const callbacks: ((need: DistributionNeed) => void)[] = [];
  vi.mocked(preflightDistribution).mockImplementation(() => new Promise((resolve) => { callbacks.push(resolve); }));
  const change = vi.fn();
  const view = render(<FleetPreflight orderIds={["old"]} onStateChange={change} />);
  view.rerender(<FleetPreflight orderIds={["new"]} onStateChange={change} />);
  const need: DistributionNeed = { orderIds: ["old"], volumes: [], eligibleTrucks: [], ineligibleTrucks: [] };
  await act(async () => callbacks[0](need));
  expect(change).not.toHaveBeenCalledWith({ selection: "old", status: "empty" });
  await act(async () => callbacks[1]({ ...need, orderIds: ["new"] }));
  expect(change).toHaveBeenLastCalledWith({ selection: "new", status: "empty" });
  fireEvent.click(screen.getByRole("button", { name: "Atualizar disponibilidade da frota" }));
  expect(change).toHaveBeenLastCalledWith({ selection: "new", status: "loading" });
  await waitFor(() => expect(preflightDistribution).toHaveBeenCalledTimes(3));
});
