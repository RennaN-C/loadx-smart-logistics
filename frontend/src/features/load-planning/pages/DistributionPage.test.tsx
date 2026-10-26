import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import type { Role } from "../../auth/types";
import { distributionAction, getDistribution, optimizeDistribution, preflightDistribution, reprocessDistributionPart } from "../api/distributionsApi";
import { getLoadPlanContinuity } from "../api/loadPlansApi";
import { makeDistribution } from "../testing/distributionFixtures";
import type { LoadDistribution } from "../types";
import { DistributionPage } from "./DistributionPage";
vi.mock("../api/distributionsApi", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/distributionsApi")>(),
  getDistribution: vi.fn(), distributionAction: vi.fn(), optimizeDistribution: vi.fn(),
  preflightDistribution: vi.fn(), reprocessDistributionPart: vi.fn(),
}));
vi.mock("../api/loadPlansApi", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/loadPlansApi")>(),
  getLoadPlan: vi.fn(), listLoadPlans: vi.fn(), getLoadPlanContinuity: vi.fn(),
  createLoadPlan: vi.fn(), approveLoadPlan: vi.fn(), recalculateLoadPlan: vi.fn(),
}));
vi.mock("../../auth/hooks/useAuth");
vi.mock("../../load-visualization/components/LoadViewer", () => ({ LoadViewer: ({ planId }: { planId: string }) => <div data-testid="scene">Cena {planId}</div> }));
function role(role: Role, permissions?: string[]) {
  vi.mocked(useAuth).mockReturnValue({ status: "authenticated", user: { id: "u1", name: "Pessoa fictícia", email: "test@example.test", role, permissions, active: true, createdAt: "2026-10-20T12:00:00Z" }, login: vi.fn(), logout: vi.fn(), updateUser: vi.fn() });
}
function setup(path = "/planning/distributions/distribution-1") {
  return render(<MemoryRouter initialEntries={[path]}><Link to="/products">Produtos</Link><Link to="/planning/distributions/distribution-1">Retomar distribuição</Link><Routes>
    <Route path="/planning/distributions/:distributionId" element={<DistributionPage />} />
    <Route path="/products" element={<div>Cadastro de produtos</div>} />
  </Routes></MemoryRouter>);
}
beforeEach(() => { vi.resetAllMocks(); role("LOGISTICS_MANAGER"); vi.mocked(getDistribution).mockResolvedValue(makeDistribution()); vi.mocked(getLoadPlanContinuity).mockResolvedValue({ loading_session: null, trip: null, operational_ready: false }); });
describe("distribuição persistida", () => {
  it.each([1, 2, 3])("mostra %i veículos com volumes próprios", async (count) => {
    vi.mocked(getDistribution).mockResolvedValue(makeDistribution(count)); setup();
    const vehicles = await screen.findByRole("group", { name: "Caminhões da distribuição" });
    expect(within(vehicles).getAllByRole("button")).toHaveLength(count);
    expect(screen.getByText(`Volume 1 de ${count} · item order-it`)).toBeInTheDocument();
    expect(optimizeDistribution).not.toHaveBeenCalled();
  });
  it("troca métricas e cena sem recalcular, incluindo URL de parte", async () => {
    setup(); await screen.findByText("Carga de TST1A23");
    fireEvent.click(screen.getByRole("tab", { name: "Visualização 3D" }));
    expect(await screen.findByTestId("scene")).toHaveTextContent("plan-1");
    fireEvent.click(screen.getByRole("button", { name: /Caminhão 2/ }));
    expect(screen.getByText("Carga de TST2A23")).toBeInTheDocument();
    expect(screen.getByTestId("scene")).toHaveTextContent("plan-2");
    expect(getDistribution).toHaveBeenCalledTimes(1); expect(optimizeDistribution).not.toHaveBeenCalled();
  });
  it("restaura parte após F5 e reencontra após visitar Produtos", async () => {
    const view = setup("/planning/distributions/distribution-1?part=part-2");
    expect(await screen.findByText("Carga de TST2A23")).toBeInTheDocument(); view.unmount();
    setup("/planning/distributions/distribution-1?part=part-2");
    expect(await screen.findByText("Carga de TST2A23")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Produtos" }));
    fireEvent.click(screen.getByRole("link", { name: "Retomar distribuição" }));
    await screen.findByText("Carga de TST1A23"); expect(getDistribution).toHaveBeenCalledTimes(3);
    expect(optimizeDistribution).not.toHaveBeenCalled();
  });
  it("aprova agregado e consulta continuidade real da parte selecionada", async () => {
    vi.mocked(distributionAction).mockResolvedValue(makeDistribution(2, "APPROVED")); setup();
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar distribuição completa" }));
    expect(await screen.findByText("Aprovada")).toBeInTheDocument();
    expect(distributionAction).toHaveBeenCalledWith("distribution-1", "approve");
    await waitFor(() => expect(getLoadPlanContinuity).toHaveBeenCalledWith("plan-1"));
    expect(screen.queryByText(/depende da OC90/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Iniciar carregamento/ })).not.toBeInTheDocument();
  });
  it("aprovação parcial não oferece operação", async () => {
    const partial = makeDistribution(2, "PARTIALLY_APPROVED"); partial.parts[0].status = "APPROVED";
    vi.mocked(distributionAction).mockResolvedValue(partial); setup();
    fireEvent.click(await screen.findByRole("button", { name: "Aceitar esta parte" }));
    await screen.findByText("Parcialmente aprovada"); expect(distributionAction).toHaveBeenCalledWith("distribution-1", "approve", "part-1");
    expect(getLoadPlanContinuity).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Aceitar esta parte" })).not.toBeInTheDocument();
  });
  it("não dispara aprovação em duplicidade", async () => {
    let finish!: (result: LoadDistribution) => void;
    vi.mocked(distributionAction).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    setup(); const button = await screen.findByRole("button", { name: "Aprovar distribuição completa" });
    fireEvent.click(button); fireEvent.click(button); expect(distributionAction).toHaveBeenCalledTimes(1);
    await act(async () => finish(makeDistribution(2, "APPROVED")));
  });
  it.each(["DISTRIBUTION_VERSION_CONFLICT", "TRUCK_OPERATION_CONFLICT", "NETWORK_ERROR"])("mantém proposta após %s e exige atualização", async (code) => {
    vi.mocked(distributionAction).mockRejectedValue(new ApiError(code, "Falha real da API", [], 409)); setup();
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar distribuição completa" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument(); expect(screen.getByText("Carga de TST1A23")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprovar distribuição completa" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar distribuição" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Aprovar distribuição completa" })).toBeEnabled());
    expect(getDistribution).toHaveBeenCalledTimes(2);
  });
  it.each(["DISTRIBUTION_NOT_FOUND", "NETWORK_ERROR", "AUTH_INVALID_TOKEN", "SERVICE_UNAVAILABLE"])("trata %s e permite consultar novamente", async (code) => {
    vi.mocked(getDistribution).mockRejectedValueOnce(new ApiError(code, "Falha", [], 404)); setup();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar distribuição" }));
    expect(await screen.findByText("Carga de TST1A23")).toBeInTheDocument();
    expect(optimizeDistribution).not.toHaveBeenCalled();
  });
  it.each(["ADMIN", "LOGISTICS_MANAGER"] as const)("permite gestão a %s conforme catálogo efetivo", async (profile) => { role(profile); setup(); expect(await screen.findByRole("button", { name: "Aprovar distribuição completa" })).toBeEnabled(); });
  it("CHECKER consulta somente aprovado sem ações", async () => {
    role("CHECKER"); vi.mocked(getDistribution).mockResolvedValue(makeDistribution(2, "APPROVED")); setup();
    await screen.findByText("Carga de TST1A23"); expect(screen.queryByRole("button", { name: /Aprovar distribuição/ })).not.toBeInTheDocument();
  });
  it("não mostra proposta não aprovada a CHECKER", async () => { role("CHECKER"); setup(); await waitFor(() => expect(getDistribution).toHaveBeenCalled()); expect(screen.queryByText("Carga de TST1A23")).not.toBeInTheDocument(); });
  it("DRIVER não consulta API", () => { role("DRIVER"); setup(); expect(screen.getByRole("alert")).toHaveTextContent("não tem acesso"); expect(getDistribution).not.toHaveBeenCalled(); });
  it("permissão flexível de leitura não ganha gestão por role", async () => {
    role("ADMIN", ["loadx.planning.read"]); setup(); await screen.findByText("Carga de TST1A23");
    expect(screen.queryByRole("button", { name: "Aprovar distribuição completa" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancelar distribuição" })).not.toBeInTheDocument();
  });
  it("cancela parte mediante confirmação e reprocessa com versão esperada", async () => {
    const incomplete = makeDistribution(2, "INCOMPLETE"); incomplete.parts[0].status = "CANCELED";
    vi.mocked(distributionAction).mockResolvedValue(incomplete);
    vi.mocked(preflightDistribution).mockResolvedValue({ orderIds: ["order-1"], volumes: [], eligibleTrucks: [makeDistribution().parts[0].truck], ineligibleTrucks: [] });
    vi.mocked(reprocessDistributionPart).mockResolvedValue(makeDistribution()); setup();
    fireEvent.click(await screen.findByRole("button", { name: "Cancelar esta parte" })); expect(distributionAction).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar cancelamento da parte" }));
    expect(await screen.findByText("Incompleta")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Aprovar distribuição completa" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Consultar caminhões para reprocessar" }));
    fireEvent.change(await screen.findByLabelText("Caminhão elegível"), { target: { value: "truck-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Reprocessar esta parte" }));
    await waitFor(() => expect(reprocessDistributionPart).toHaveBeenCalledWith("distribution-1", "part-1", "truck-1", "plan-1"));
    expect(await screen.findByRole("button", { name: "Aceitar esta parte" })).toBeInTheDocument();
  });
  it("cancelamento total preserva consulta e remove ações", async () => {
    vi.mocked(distributionAction).mockResolvedValue(makeDistribution(2, "CANCELED")); setup();
    fireEvent.click(await screen.findByRole("button", { name: "Cancelar distribuição" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar cancelamento" })); await screen.findByText("Cancelada");
    expect(screen.getByText("Carga de TST1A23")).toBeInTheDocument(); expect(screen.queryByRole("button", { name: "Aprovar distribuição completa" })).not.toBeInTheDocument();
  });
});
