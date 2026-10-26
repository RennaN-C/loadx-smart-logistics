import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { explainLoadPlan } from "../api/loadPlansApi";
import { PlanAIExplanation } from "./PlanAIExplanation";

vi.mock("../api/loadPlansApi", () => ({ explainLoadPlan: vi.fn() }));
beforeEach(() => { vi.clearAllMocks(); });

it("só chama a explicação após uma ação explícita, sem recalcular o plano", async () => {
  vi.mocked(explainLoadPlan).mockResolvedValue({
    loadPlanId: "p1", source: "AI", explanation: "Boa ocupação.", algorithmVersion: "v1",
  });
  render(<PlanAIExplanation planId="p1" />);
  expect(explainLoadPlan).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Solicitar explicação do plano" }));
  expect(await screen.findByText("Explicação gerada por IA")).toBeInTheDocument();
  expect(screen.getByText("Boa ocupação.")).toBeInTheDocument();
  expect(explainLoadPlan).toHaveBeenCalledWith("p1");
});

it("identifica fallback sem atribuir a resposta à IA", async () => {
  vi.mocked(explainLoadPlan).mockResolvedValue({
    loadPlanId: "p1", source: "FALLBACK", explanation: "Resumo determinístico.", algorithmVersion: "v1",
  });
  render(<PlanAIExplanation planId="p1" />);
  fireEvent.click(screen.getByRole("button", { name: "Solicitar explicação do plano" }));
  expect(await screen.findByText("Resumo automático (IA indisponível)")).toBeInTheDocument();
  expect(screen.getByText("Resumo determinístico.")).toBeInTheDocument();
});

it("falha na explicação sem alterar o plano", async () => {
  vi.mocked(explainLoadPlan).mockRejectedValue(new Error("Provedor indisponível"));
  render(<PlanAIExplanation planId="p1" />);
  fireEvent.click(screen.getByRole("button", { name: "Solicitar explicação do plano" }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("não foi alterado"));
});
