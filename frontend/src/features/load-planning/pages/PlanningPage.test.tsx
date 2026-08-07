import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import { listTrucks } from "../../trucks/api/trucksApi";
import { approveLoadPlan, createLoadPlan, getLoadPlan, recalculateLoadPlan } from "../api/loadPlansApi";
import type { LoadPlan, LoadPlanItem } from "../types";
import { PlanningPage } from "./PlanningPage";

vi.mock("../api/loadPlansApi");
vi.mock("../../trucks/api/trucksApi");
vi.mock("../../orders/api/ordersApi");
vi.mock("../../customers/api/customersApi");
vi.mock("../../auth/hooks/useAuth");

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
    expect(await screen.findByText("19,2%")).toBeInTheDocument();
  });

  it("carrega o plano da URL, já que o backend não lista planos", async () => {
    vi.mocked(getLoadPlan).mockResolvedValue(makePlan());

    renderAt("/planning/lp1");

    await waitFor(() => expect(getLoadPlan).toHaveBeenCalledWith("lp1"));
    expect(await screen.findByText("Calculado")).toBeInTheDocument();
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
  });

  it("traduz o erro de plano com recusa vindo do backend", async () => {
    vi.mocked(getLoadPlan).mockRejectedValue(new ApiError("LOAD_PLAN_NOT_FOUND", "x"));

    renderAt("/planning/lp1");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Este plano de carga não foi encontrado.",
    );
  });
});
