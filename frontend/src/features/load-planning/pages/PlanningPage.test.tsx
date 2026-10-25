import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import { listTruckOperationalStatus, listTrucks } from "../../trucks/api/trucksApi";
import { approveLoadPlan, createLoadPlan, getLoadPlan, getLoadPlanContinuity, listLoadPlans, recalculateLoadPlan } from "../api/loadPlansApi";
import { optimizeDistribution } from "../api/distributionsApi";
import { makeDistribution } from "../testing/distributionFixtures";
import type { LoadPlan, LoadPlanItem } from "../types";
import { PlanningPage } from "./PlanningPage";

vi.mock("../api/loadPlansApi", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/loadPlansApi")>(),
  getLoadPlan: vi.fn(), listLoadPlans: vi.fn(), getLoadPlanContinuity: vi.fn(),
  createLoadPlan: vi.fn(), approveLoadPlan: vi.fn(), recalculateLoadPlan: vi.fn(),
}));
vi.mock("../api/distributionsApi", async (importOriginal) => ({ ...await importOriginal<typeof import("../api/distributionsApi")>(), optimizeDistribution: vi.fn() }));
// WebGL nao existe em jsdom: a cena e testada pela geometria pura, em sceneGeometry.test.ts
vi.mock("../../load-visualization/components/LoadViewer", () => ({
  LoadViewer: ({ planId }: { planId: string }) => <div data-testid="viewer">cena de {planId}</div>,
}));
vi.mock("../../trucks/api/trucksApi");
vi.mock("../../orders/api/ordersApi");
vi.mock("../../customers/api/customersApi");
vi.mock("../../auth/hooks/useAuth");
vi.mock("../../audit/components/AuditTrail", () => ({
  AuditTrail: () => <div data-testid="audit-trail">histórico contextual</div>,
}));

const PLACED: LoadPlanItem = {
  id: "li1",
  orderId: "o1",
  orderItemId: "oi1",
  productId: "p1",
  volumeIndex: 1,
  quantity: 1,
  deliverySequence: 1,
  productCode: "CX-100",
  productName: "Caixa média",
  originalWidthCm: 40,
  originalHeightCm: 30,
  originalLengthCm: 60,
  weightKg: 12.5,
  fragile: false,
  stackable: true,
  rotationAllowed: true,
  xCm: 0,
  yCm: 0,
  zCm: 0,
  widthCm: 40,
  heightCm: 30,
  lengthCm: 60,
  rotationCode: "XYZ",
  loadingSequence: 1,
  placed: true,
  rejectionReason: null,
};

const REJECTED: LoadPlanItem = {
  ...PLACED,
  id: "li2",
  productCode: "PL-200",
  productName: "Pallet padrão",
  xCm: null,
  yCm: null,
  zCm: null,
  widthCm: null,
  heightCm: null,
  lengthCm: null,
  rotationCode: null,
  loadingSequence: null,
  placed: false,
  rejectionReason: "TRUCK_DIMENSIONS_EXCEEDED",
};

function makePlan(overrides: Partial<LoadPlan> = {}): LoadPlan {
  return {
    id: "lp1",
    truckId: "t1",
    recalculatedFromId: null,
    status: "CALCULATED",
    internalVolumeCm3: 37_440_000,
    usedVolumeCm3: 7_200_000,
    occupancyPercent: 19.2,
    totalWeightKg: 12.5,
    loadedCount: 1,
    unloadedCount: 0,
    algorithmVersion: "v1",
    createdAt: "2026-08-07T12:00:00Z",
    approvedAt: null,
    orderIds: ["o1"],
    items: [PLACED],
    ...overrides,
  };
}

function mockRole(role: "ADMIN" | "LOGISTICS_MANAGER" | "CHECKER" | "DRIVER") {
  vi.mocked(useAuth).mockReturnValue({
    status: "authenticated",
    user: {
      id: "u1",
      name: "Ana Souza",
      email: "ana@example.test",
      role,
      active: true,
      createdAt: "2026-08-01T00:00:00Z",
    },
    login: vi.fn(),
    updateUser: vi.fn(),
    logout: vi.fn(),
  });
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path === "/planning" ? "/planning?tab=new" : path]}>
      <Routes>
        <Route path="/planning" element={<PlanningPage />} />
        <Route path="/planning/:planId" element={<PlanningPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function calculationButton(name = "Calcular plano de carga") {
 fireEvent.click(screen.getByRole("button", { name: "Revisão" }));
 return screen.getByRole("button", { name });
}
function ordersStep() { fireEvent.click(screen.getByRole("button", { name: "Pedidos" })); }

describe("PlanningPage", () => {
  it("abre Execução dentro do planejamento sem redirecionar para Carregamentos", async () => {
    renderAt("/planning");
    const execution = screen.getByRole("link", { name: "Execução" });
    expect(execution).toHaveAttribute("href", "/planning?tab=execution");
    fireEvent.click(execution);
    expect(await screen.findByRole("heading", { name: "Execução dos planos" })).toBeVisible();
    await waitFor(() => expect(listLoadPlans).toHaveBeenLastCalledWith(expect.objectContaining({ status: "APPROVED", operationScope: "ongoing" })));
    expect(execution).toHaveAttribute("aria-current", "page");
    expect(createLoadPlan).not.toHaveBeenCalled();
  });
  it("guia pedidos, modalidade, veículo e revisão sem salvar durante a navegação", async () => {
    renderAt("/planning");
    await screen.findByRole("checkbox");
    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByRole("radio", { name: "Um caminhão" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByLabelText("CAMINHÃO")).toBeVisible();
    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByRole("heading", { name: "Revise antes de calcular" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Calcular plano de carga" })).toBeEnabled();
    ordersStep();
    expect(screen.getByRole("checkbox")).toBeChecked();
    expect(createLoadPlan).not.toHaveBeenCalled();
  });
  beforeEach(() => {
    sessionStorage.clear();
    vi.resetAllMocks();
    mockRole("LOGISTICS_MANAGER");
    vi.mocked(listLoadPlans).mockResolvedValue(makePage([]));
    vi.mocked(getLoadPlanContinuity).mockResolvedValue({ loading_session: null, trip: null, operational_ready: true });
    vi.mocked(listTrucks).mockResolvedValue(
      makePage([
        {
          id: "t1",
          plate: "ABC1D23",
          model: "Baú médio",
          internalWidthCm: 240,
          internalHeightCm: 260,
          internalLengthCm: 600,
          maxWeightKg: 8000,
          active: true,
          createdAt: "2026-08-01T00:00:00Z",
        },
        {
          id: "t2",
          plate: "OLD0X00",
          model: "Baú inativo",
          internalWidthCm: 200,
          internalHeightCm: 200,
          internalLengthCm: 400,
          maxWeightKg: 5000,
          active: false,
          createdAt: "2026-08-01T00:00:00Z",
        },
      ]),
    );
    // Situação operacional (OC67/OC72): contrato separado de `GET /trucks`, que
    // não traz disponibilidade. Por padrão os dois caminhões estão livres.
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(
      makePage([
        {
          id: "t1",
          plate: "ABC1D23",
          model: "Baú médio",
          active: true,
          hasOperationConflict: false,
          available: true,
        },
        {
          id: "t2",
          plate: "OLD0X00",
          model: "Baú inativo",
          active: false,
          hasOperationConflict: false,
          available: false,
        },
      ]),
    );
    vi.mocked(listOrders).mockResolvedValue(
      makePage([
        {
          id: "o1",
          customerId: "c1",
          status: "READY",
          priority: "NORMAL",
          expectedDeliveryAt: null,
          createdAt: "2026-08-01T00:00:00Z",
          itemCount: 2,
        },
        {
          id: "o2",
          customerId: "c1",
          status: "DRAFT",
          priority: "LOW",
          expectedDeliveryAt: null,
          createdAt: "2026-08-01T00:00:00Z",
          itemCount: 1,
        },
      ]),
    );
    vi.mocked(listCustomers).mockResolvedValue(
      makePage([
        {
          id: "c1",
          name: "Distribuidora Aurora",
          active: true,
          city: "Campinas",
          state: "SP",
          createdAt: "2026-08-01T00:00:00Z",
        },
      ]),
    );
  });

  it("otimiza pedidos sem caminhão manual e salva a proposta real", async () => {
    vi.mocked(optimizeDistribution).mockResolvedValue(makeDistribution());
    render(<MemoryRouter initialEntries={["/planning?tab=new"]}><Routes>
      <Route path="/planning" element={<PlanningPage />} />
      <Route path="/planning/distributions/:distributionId" element={<div>Distribuição persistida aberta</div>} />
    </Routes></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Modalidade" }));
    fireEvent.click(await screen.findByRole("radio", { name: /Seleção automática/ }));
    ordersStep();
    fireEvent.click(await screen.findByRole("checkbox"));
    fireEvent.click(calculationButton("Otimizar e salvar distribuição"));
    expect(await screen.findByText("Distribuição persistida aberta")).toBeInTheDocument();
    expect(optimizeDistribution).toHaveBeenCalledWith(["o1"], expect.any(String));
    expect(createLoadPlan).not.toHaveBeenCalled();
  });

  it.each(["DISTRIBUTION_CAPACITY_INSUFFICIENT", "TRUCK_OPERATION_CONFLICT", "LOAD_PLAN_ORDER_NOT_ELIGIBLE"])("preserva seleção e trata %s", async (code) => {
    vi.mocked(optimizeDistribution).mockRejectedValue(new ApiError(code, "Resposta real", [{ volume_index: 1 }], 422));
    renderAt("/planning");
    fireEvent.click(screen.getByRole("button", { name: "Modalidade" }));
    fireEvent.click(await screen.findByRole("radio", { name: /Seleção automática/ }));
    ordersStep();
    fireEvent.click(await screen.findByRole("checkbox"));
    fireEvent.click(calculationButton("Otimizar e salvar distribuição"));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    ordersStep();
    expect(screen.getByRole("checkbox")).toBeChecked();
    expect(calculationButton("Otimizar e salvar distribuição")).toBeEnabled();
    expect(createLoadPlan).not.toHaveBeenCalled();
  });

  it("plano de distribuição não usa aprovação ou recálculo legados", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan({ distributionId: "distribution-1" }));
    renderAt("/planning/lp1");
    expect(await screen.findByRole("link", { name: "Abrir distribuição completa" })).toHaveAttribute("href", "/planning/distributions/distribution-1");
    expect(screen.queryByRole("button", { name: "Aprovar plano" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Recalcular" })).not.toBeInTheDocument();
  });

  it("oferece só caminhão ativo e pedido pronto", async () => {
    renderAt("/planning");

    await screen.findByLabelText("CAMINHÃO");

    const trucks = [...screen.getByLabelText("CAMINHÃO").querySelectorAll("option")].map((o) => o.value);
    expect(trucks).toContain("t1");
    expect(trucks).not.toContain("t2"); // inativo

    expect(screen.getByText("Distribuidora Aurora")).toBeInTheDocument();
    expect(screen.getAllByRole("checkbox")).toHaveLength(1); // só o READY
  });

  it("avisa sem bloquear o caminhão em operação, conforme o backend", async () => {
    // `create_load_plan` recusa caminhão INATIVO e só. O conflito vem da OC67,
    // aparece para orientar o usuário, mas não cria uma trava que a API não tem.
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(
      makePage([
        {
          id: "t1",
          plate: "ABC1D23",
          model: "Baú médio",
          active: true,
          hasOperationConflict: true,
          available: false,
        },
      ]),
    );

    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");

    const opcao = [...screen.getByLabelText("CAMINHÃO").querySelectorAll("option")].find(
      (o) => o.value === "t1",
    );
    expect(opcao?.textContent).toContain("em operação");
    expect(opcao).not.toBeDisabled();
  });

  it("caminhão livre aparece sem aviso nenhum", async () => {
    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");

    const opcao = [...screen.getByLabelText("CAMINHÃO").querySelectorAll("option")].find(
      (o) => o.value === "t1",
    );
    expect(opcao?.textContent).not.toContain("em operação");
  });

  it("caminhão sem situação conhecida continua selecionável, sem aviso", async () => {
    // A consulta de situação pode falhar ou não trazer todos. Esconder a opção
    // tiraria do usuário um caminhão que o backend aceitaria.
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([]));

    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");

    const opcoes = [...screen.getByLabelText("CAMINHÃO").querySelectorAll("option")];
    const t1 = opcoes.find((o) => o.value === "t1");
    expect(t1).toBeDefined();
    expect(t1?.textContent).not.toContain("em operação");
  });

  it("não confunde erro ao carregar caminhões com lista vazia e permite tentar novamente", async () => {
    vi.mocked(listTrucks).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "Falha de rede."));
    renderAt("/planning");

    expect(await screen.findByText(/Não foi possível carregar os dados necessários para planejar/)).toBeInTheDocument();
    expect(screen.queryByText(/Nenhum pedido pronto para planejar/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByLabelText("CAMINHÃO")).toBeInTheDocument();
    expect(listTrucks).toHaveBeenCalledTimes(2);
  });


  it.each(["orders", "availability"])("oferece retry quando a consulta de %s falha", async (source) => {
    const load = source === "orders" ? listOrders : listTruckOperationalStatus;
    vi.mocked(load).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "Falha de rede."));
    renderAt("/planning");
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível carregar");
    expect(screen.queryByLabelText("CAMINHÃO")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByLabelText("CAMINHÃO")).toBeInTheDocument();
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("anuncia carregamento enquanto aguarda a disponibilidade", async () => {
    vi.mocked(listTruckOperationalStatus).mockImplementationOnce(() => new Promise(() => {}));
    renderAt("/planning");
    expect(screen.getByRole("status")).toHaveTextContent("Carregando caminhões e pedidos");
    expect(screen.queryByLabelText("CAMINHÃO")).not.toBeInTheDocument();
    expect(screen.queryByText(/Nenhum pedido pronto/)).not.toBeInTheDocument();
  });

  it("só habilita o cálculo com caminhão e ao menos um pedido", async () => {
    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");

    const button = calculationButton();
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    expect(button).toBeDisabled();

    ordersStep();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(button).toBeEnabled();
  });

  it.each([
    [200, false],
    [201, true],
  ])("diferencia item da quantidade de %i volumes e bloqueia apenas acima do limite", async (volumes, exceeds) => {
    vi.mocked(listOrders).mockResolvedValue(makePage([{
      id: "o1",
      customerId: "c1",
      status: "READY",
      priority: "NORMAL",
      expectedDeliveryAt: null,
      createdAt: "2026-08-01T00:00:00Z",
      itemCount: 1,
      volumeCount: volumes,
    }]));

    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");
    expect(screen.getByText(new RegExp(`1 item.*${volumes} volumes`))).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    ordersStep();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByText(`${volumes} de 200 volumes físicos`)).toBeInTheDocument();
    if (exceeds) {
      expect(calculationButton()).toBeDisabled();
    } else {
      expect(calculationButton()).toBeEnabled();
    }
    if (exceeds) {
      expect(screen.getByRole("alert")).toHaveTextContent("Desmarque pedidos");
      expect(screen.getByRole("link", { name: "Pedidos" })).toHaveAttribute("href", "/orders");
    }
  });

  it("soma volumes físicos de dois pedidos e impede o cálculo acima de 200", async () => {
    vi.mocked(listOrders).mockResolvedValue(makePage([120, 90].map((count, index) => ({
      id: `o${index + 1}`,
      customerId: "c1",
      status: "READY" as const,
      priority: "NORMAL" as const,
      expectedDeliveryAt: null,
      createdAt: "2026-08-01T00:00:00Z",
      itemCount: 1,
      volumeCount: count,
    }))));

    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");
    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    ordersStep();
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(screen.getByText("120 de 200 volumes físicos")).toBeInTheDocument();
    fireEvent.click(checkboxes[1]);
    expect(screen.getByText("210 de 200 volumes físicos")).toBeInTheDocument();
    expect(calculationButton()).toBeDisabled();
    fireEvent.click(checkboxes[1]);
    expect(calculationButton()).toBeEnabled();
  });

  it("traduz erro 422 do servidor com contagem efetiva se os pedidos mudarem", async () => {
    vi.mocked(listOrders).mockResolvedValue(makePage([{
      id: "o1", customerId: "c1", status: "READY", priority: "NORMAL",
      expectedDeliveryAt: null, createdAt: "2026-08-01T00:00:00Z", itemCount: 1,
      volumeCount: 190,
    }]));
    vi.mocked(createLoadPlan).mockRejectedValue(new ApiError(
      "LOAD_PLAN_VOLUME_LIMIT_EXCEEDED",
      "O plano excede o limite síncrono de volumes.",
      [{ field: "order_ids", volume_count: 215, max_volumes: 200 }],
      422,
    ));
    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");
    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    ordersStep();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(calculationButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("215 volumes físicos");
    expect(createLoadPlan).toHaveBeenCalledOnce();
  });

  it("calcula e mostra as métricas do plano", async () => {
    vi.mocked(createLoadPlan).mockResolvedValue(makePlan());
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());

    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");

    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    ordersStep();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(calculationButton());

    await waitFor(() => expect(createLoadPlan).toHaveBeenCalledWith({ truckId: "t1", orderIds: ["o1"] }));
    await waitFor(() => expect(getLoadPlan).toHaveBeenCalledWith("lp1"));
    expect(await screen.findByText("19,2%")).toBeInTheDocument();
  });

  it("carrega o plano da URL, já que o backend não lista planos", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());

    renderAt("/planning/lp1");

    await waitFor(() => expect(getLoadPlan).toHaveBeenCalledWith("lp1"));
    expect(await screen.findByText("Calculado")).toBeInTheDocument();
    expect(screen.getByTestId("audit-trail")).toBeInTheDocument();
  });

  it("lista a sequência de carregamento e traduz a rotação", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());

    renderAt("/planning/lp1");

    expect(await screen.findByText("Sequência de carregamento")).toBeInTheDocument();
    expect(screen.getByText("Sem rotação")).toBeInTheDocument();
    expect(screen.getByText("0, 0, 0 cm")).toBeInTheDocument();
  });

  it("mostra o motivo de cada volume recusado e bloqueia a aprovação", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(
      makePlan({ items: [PLACED, REJECTED], unloadedCount: 1, loadedCount: 1 }),
    );

    renderAt("/planning/lp1");

    expect(await screen.findByText("Volumes que ficaram de fora")).toBeInTheDocument();
    expect(screen.getByText("Não cabe nas medidas do baú")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprovar plano" })).toBeDisabled();
  });

  it("aprova quando não há recusa", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());
    vi.mocked(approveLoadPlan).mockResolvedValue(makePlan({ status: "APPROVED" }));

    renderAt("/planning/lp1");
    await screen.findByText("Calculado");

    fireEvent.click(screen.getByRole("button", { name: "Aprovar plano" }));

    await waitFor(() => expect(approveLoadPlan).toHaveBeenCalledWith("lp1"));
    expect(await screen.findByText("Aprovado")).toBeInTheDocument();
  });

  it("recalcular gera plano novo e a tela passa a carregar pelo id novo", async () => {
    const recalculated = makePlan({ id: "lp2", recalculatedFromId: "lp1" });
    vi.mocked(getLoadPlan).mockImplementation(async (id) =>
      id === "lp2" ? recalculated : makePlan(),
    );
    vi.mocked(recalculateLoadPlan).mockResolvedValue(recalculated);

    renderAt("/planning/lp1");
    await screen.findByText("Calculado");

    fireEvent.click(screen.getByRole("button", { name: "Recalcular" }));

    await waitFor(() => expect(recalculateLoadPlan).toHaveBeenCalledWith("lp1"));
    // a URL mudou, e o plano vem do backend pelo id novo — sem duas fontes de verdade
    await waitFor(() => expect(getLoadPlan).toHaveBeenCalledWith("lp2"));
    expect(await screen.findByText(/recalculado de um plano anterior/)).toBeInTheDocument();
  });

  it("esconde as ações para quem só lê", async () => {
    mockRole("CHECKER");
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan({ status: "APPROVED" }));

    renderAt("/planning/lp1");
    await screen.findByText("Aprovado");

    expect(screen.queryByRole("button", { name: "Aprovar plano" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Recalcular" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("audit-trail")).not.toBeInTheDocument();
  });

  it("traduz o erro de plano com recusa vindo do backend", async () => {
    vi.mocked(getLoadPlan).mockRejectedValue(new ApiError("LOAD_PLAN_NOT_FOUND", "x"));

    renderAt("/planning/lp1");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Este plano de carga não foi encontrado.",
    );
  });

  it("mostra a cena 3D na aba de visualização", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());

    renderAt("/planning/lp1");
    await screen.findByText("Calculado");

    expect(screen.queryByTestId("viewer")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Visualização 3D" }));

    expect(await screen.findByTestId("viewer")).toHaveTextContent("cena de lp1");
  });
  it("oferece retorno e vínculos de pedidos em plano persistido", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan({ status: "APPROVED" }));
    renderAt("/planning/lp1");
    await screen.findByText("Aprovado");
    expect(screen.getByRole("link", { name: "Voltar aos pedidos" })).toHaveAttribute("href", "/orders");
    expect(screen.getByRole("link", { name: "Abrir este plano" })).toHaveAttribute("href", "/planning/lp1");
    expect(screen.getAllByRole("link", { name: "Ver pedido" })[0]).toHaveAttribute("href", "/orders?order=o1");
  });

  it("preserva caminhos de retorno quando o plano não existe", async () => {
    vi.mocked(getLoadPlan).mockRejectedValue(new ApiError("LOAD_PLAN_NOT_FOUND", "x"));
    renderAt("/planning/lp1");
    await screen.findByRole("alert");
    expect(screen.getByRole("link", { name: "Voltar ao planejamento" })).toHaveAttribute("href", "/planning");
  });

  it("recalcular plano anterior não redireciona após abrir outro registro", async () => {
    vi.mocked(getLoadPlan).mockImplementation(async (id) => makePlan({ id }));
    let complete!: (plan: LoadPlan) => void;
    vi.mocked(recalculateLoadPlan).mockImplementation(() => new Promise((resolve) => { complete = resolve; }));
    render(<MemoryRouter initialEntries={["/planning/lp1"]}>
      <Link to="/planning/lp2">Outro registro</Link>
      <Routes><Route path="/planning/:planId" element={<PlanningPage />} /></Routes>
    </MemoryRouter>);
    await screen.findByText("Calculado");
    fireEvent.click(screen.getByRole("button", { name: "Recalcular" }));
    fireEvent.click(screen.getByRole("link", { name: "Outro registro" }));
    await waitFor(() => expect(screen.getByRole("link", { name: "Abrir este plano" })).toHaveAttribute("href", "/planning/lp2"));
    await act(async () => { complete(makePlan({ id: "lp3" })); });
    expect(screen.getByRole("link", { name: "Abrir este plano" })).toHaveAttribute("href", "/planning/lp2");
  });

  it("recálculo concluído após sair não interrompe a tela de destino", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());
    let complete!: (plan: LoadPlan) => void;
    vi.mocked(recalculateLoadPlan).mockImplementation(() => new Promise((resolve) => { complete = resolve; }));
    render(<MemoryRouter initialEntries={["/planning/lp1"]}>
      <Link to="/orders">Sair da operação</Link>
      <Routes>
        <Route path="/planning/:planId" element={<PlanningPage />} />
        <Route path="/orders" element={<h1>Lista de pedidos</h1>} />
      </Routes>
    </MemoryRouter>);
    await screen.findByText("Calculado");
    fireEvent.click(screen.getByRole("button", { name: "Recalcular" }));
    fireEvent.click(screen.getByRole("link", { name: "Sair da operação" }));
    await screen.findByText("Lista de pedidos");
    await act(async () => { complete(makePlan({ id: "lp3" })); });
    expect(screen.getByText("Lista de pedidos")).toBeInTheDocument();
  });

  it("cálculo concluído após sair não força reentrada no planejamento", async () => {
    let complete!: (plan: LoadPlan) => void;
    vi.mocked(createLoadPlan).mockImplementation(() => new Promise((resolve) => { complete = resolve; }));
    render(<MemoryRouter initialEntries={["/planning?tab=new"]}>
      <Link to="/orders">Sair da operação</Link>
      <Routes>
        <Route path="/planning" element={<PlanningPage />} />
        <Route path="/planning/:planId" element={<PlanningPage />} />
        <Route path="/orders" element={<h1>Lista de pedidos</h1>} />
      </Routes>
    </MemoryRouter>);
    await screen.findByLabelText("CAMINHÃO");
    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    ordersStep();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(calculationButton());
    await waitFor(() => expect(createLoadPlan).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("link", { name: "Sair da operação" }));
    await screen.findByText("Lista de pedidos");
    await act(async () => { complete(makePlan({ id: "lp3" })); });
    expect(screen.getByText("Lista de pedidos")).toBeInTheDocument();
  });

});


it("OC100 remove caminhão em manutenção da seleção de planejamento", async () => {
  vi.mocked(listTrucks).mockResolvedValue(makePage([{ id: "t-maint", plate: "ABC1D23", model: "Baú", active: true, internalWidthCm: 100, internalHeightCm: 100, internalLengthCm: 100, maxWeightKg: 1000, createdAt: "2026-01-01T00:00:00Z" }]));
  vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([{ id: "t-maint", plate: "ABC1D23", model: "Baú", active: true, hasOperationConflict: false, hasMaintenanceConflict: true, available: false }]));
  vi.mocked(listOrders).mockResolvedValue(makePage([]));
  vi.mocked(listCustomers).mockResolvedValue(makePage([]));
  vi.mocked(useAuth).mockReturnValue({ user: { id: "u1", name: "Gestor", email: "manager@example.test", role: "LOGISTICS_MANAGER", active: true, createdAt: "2026-01-01T00:00:00Z" }, status: "authenticated", login: vi.fn(), updateUser: vi.fn(), logout: vi.fn() });
  renderAt("/planning");
  await screen.findByLabelText("CAMINHÃO");
  expect(screen.queryByRole("option", { name: /ABC1D23/ })).not.toBeInTheDocument();
});


describe("PlanningPage — entrada e autorização da retomada", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.resetAllMocks();
    vi.mocked(listLoadPlans).mockResolvedValue(makePage([]));
  });
  it.each(["ADMIN", "LOGISTICS_MANAGER", "CHECKER"] as const)("%s entra na listagem sem criar plano", async (role) => {
    mockRole(role);
    render(<MemoryRouter initialEntries={["/planning"]}><PlanningPage /></MemoryRouter>);
    await screen.findByText("Nenhum plano nesta consulta");
    expect(createLoadPlan).not.toHaveBeenCalled();
    expect(listTrucks).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("CAMINHÃO")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Novo planejamento" }) !== null).toBe(role !== "CHECKER");
  });
  it("DRIVER não consulta lista global nem detalhe mesmo por URL", () => {
    mockRole("DRIVER");
    renderAt("/planning/lp1");
    expect(screen.getByRole("alert")).toHaveTextContent("não tem acesso");
    expect(listLoadPlans).not.toHaveBeenCalled();
    expect(getLoadPlan).not.toHaveBeenCalled();
  });
});


it("permite retentar o detalhe persistido sem criar nem recalcular", async () => {
  vi.resetAllMocks();
  mockRole("LOGISTICS_MANAGER");
  vi.mocked(getLoadPlan).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "Falha de rede")).mockResolvedValue(makePlan());
  renderAt("/planning/lp1");
  fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Resultado do cálculo")).toBeInTheDocument();
  expect(getLoadPlan).toHaveBeenCalledTimes(2);
  expect(createLoadPlan).not.toHaveBeenCalled();
  expect(recalculateLoadPlan).not.toHaveBeenCalled();
});

it("bloqueia aprovacao e recalculo quando o servidor informa pedidos fora de READY", async () => {
  vi.mocked(getLoadPlan).mockResolvedValue(makePlan({ ordersReadyForApproval: false }));
  renderAt("/planning/lp1");
  expect(await screen.findByRole("button", { name: "Aprovar plano" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Recalcular" })).toBeDisabled();
  expect(screen.getByRole("status")).toHaveTextContent("já saíram da fila de planejamento");
  expect(approveLoadPlan).not.toHaveBeenCalled();
});
