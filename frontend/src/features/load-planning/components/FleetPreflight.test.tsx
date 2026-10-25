import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { preflightDistribution } from "../api/distributionsApi";
import { FleetPreflight } from "./FleetPreflight";

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
