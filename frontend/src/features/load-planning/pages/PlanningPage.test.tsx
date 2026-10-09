import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import { listTruckOperationalStatus, listTrucks } from "../../trucks/api/trucksApi";
import { approveLoadPlan, createLoadPlan, getLoadPlan, recalculateLoadPlan } from "../api/loadPlansApi";
import type { LoadPlan, LoadPlanItem } from "../types";
import { PlanningPage } from "./PlanningPage";

vi.mock("../api/loadPlansApi");
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

function mockRole(role: "LOGISTICS_MANAGER" | "CHECKER") {
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
    logout: vi.fn(),
  });
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/planning" element={<PlanningPage />} />
        <Route path="/planning/:planId" element={<PlanningPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PlanningPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockRole("LOGISTICS_MANAGER");
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

  it("só habilita o cálculo com caminhão e ao menos um pedido", async () => {
    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");

    const button = screen.getByRole("button", { name: "Calcular plano de carga" });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    expect(button).toBeDisabled();

    fireEvent.click(screen.getByRole("checkbox"));
    expect(button).toBeEnabled();
  });

  it("calcula e mostra as métricas do plano", async () => {
    vi.mocked(createLoadPlan).mockResolvedValue(makePlan());
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());

    renderAt("/planning");
    await screen.findByLabelText("CAMINHÃO");

    fireEvent.change(screen.getByLabelText("CAMINHÃO"), { target: { value: "t1" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Calcular plano de carga" }));

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
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());

    renderAt("/planning/lp1");
    await screen.findByText("Calculado");

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
});


it("OC100 remove caminhão em manutenção da seleção de planejamento", async () => {
  vi.mocked(listTrucks).mockResolvedValue(makePage([{ id: "t-maint", plate: "ABC1D23", model: "Baú", active: true, internalWidthCm: 100, internalHeightCm: 100, internalLengthCm: 100, maxWeightKg: 1000, createdAt: "2026-01-01T00:00:00Z" }]));
  vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([{ id: "t-maint", plate: "ABC1D23", model: "Baú", active: true, hasOperationConflict: false, hasMaintenanceConflict: true, available: false }]));
  vi.mocked(listOrders).mockResolvedValue(makePage([]));
  vi.mocked(listCustomers).mockResolvedValue(makePage([]));
  vi.mocked(useAuth).mockReturnValue({ user: { id: "u1", name: "Gestor", email: "manager@example.test", role: "LOGISTICS_MANAGER", active: true, createdAt: "2026-01-01T00:00:00Z" }, status: "authenticated", login: vi.fn(), logout: vi.fn() });
  renderAt("/planning");
  await screen.findByLabelText("CAMINHÃO");
  expect(screen.queryByRole("option", { name: /ABC1D23/ })).not.toBeInTheDocument();
});
