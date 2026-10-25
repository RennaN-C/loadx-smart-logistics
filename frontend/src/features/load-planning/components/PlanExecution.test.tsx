import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { makePage } from "../../../tests/makePage";
import { listLoadPlans } from "../api/loadPlansApi";
import { PlanExecution } from "./PlanExecution";

vi.mock("../api/loadPlansApi", () => ({ listLoadPlans: vi.fn() }));
beforeEach(() => { vi.resetAllMocks(); });
function show() { render(<MemoryRouter initialEntries={["/planning?tab=execution"]}><PlanExecution /></MemoryRouter>); }

it("consulta planos aprovados e mantém o acompanhamento no planejamento", async () => {
  vi.mocked(listLoadPlans).mockResolvedValue(makePage([{ id: "p1", truckId: "t1", truckPlate: "ABC1D23", truckModel: "Baú", status: "APPROVED", distributionId: null, createdAt: "2026-10-25T00:00:00Z", recalculatedFromId: null, loadedCount: 10, unloadedCount: 0, occupancyPercent: 32, totalWeightKg: 100, orderCount: 1, operation: null }]));
  show();
  await screen.findByRole("table", { name: "Execução dos planos aprovados" });
  expect(listLoadPlans).toHaveBeenCalledWith({ page: 1, pageSize: 20, status: "APPROVED", operationScope: "ongoing" });
  expect(screen.getByRole("link", { name: "Abrir planejamento" })).toHaveAttribute("href", "/planning/p1");
  fireEvent.change(screen.getByLabelText("Situação operacional"), { target: { value: "completed" } });
  await waitFor(() => expect(listLoadPlans).toHaveBeenLastCalledWith(expect.objectContaining({ operationScope: "completed" })));
});

it("distingue erro de lista vazia e permite repetir a consulta", async () => {
  vi.mocked(listLoadPlans).mockRejectedValueOnce(new Error("offline")).mockResolvedValue(makePage([]));
  show();
  expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível consultar");
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Nenhuma operação encontrada com esse filtro.")).toBeInTheDocument();
});
