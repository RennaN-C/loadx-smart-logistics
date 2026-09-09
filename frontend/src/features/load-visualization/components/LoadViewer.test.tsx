import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getLoadPlanVisualization } from "../../load-planning/api/loadPlansApi";
import type { LoadPlan, LoadPlanVisualization, PlacedItem } from "../../load-planning/types";
import { LoadViewer } from "./LoadViewer";
import type { LoadSceneProps } from "./LoadScene";

vi.mock("../../load-planning/api/loadPlansApi");

/** A cena precisa de WebGL, que não existe em jsdom: aqui só guardamos as props. */
const cenaProps: LoadSceneProps[] = [];
vi.mock("./LoadScene", () => ({
  LoadScene: (props: LoadSceneProps) => {
    cenaProps.push(props);
    return <div data-testid="cena" />;
  },
}));

const TRUCK = {
  id: "t1",
  plate: "ABC1D23",
  model: "Baú",
  widthCm: 240,
  heightCm: 260,
  lengthCm: 600,
  maxWeightKg: 8000,
};

function item(index: number): PlacedItem {
  return {
    id: `v${index}`,
    orderId: "o1",
    orderItemId: "oi1",
    productId: "p1",
    volumeIndex: 1,
    quantity: 1,
    deliverySequence: 1,
    productCode: `COD-${index}`,
    productName: `Produto ${index}`,
    originalWidthCm: 40,
    originalHeightCm: 30,
    originalLengthCm: 60,
    weightKg: 10,
    fragile: false,
    stackable: true,
    rotationAllowed: true,
    xCm: 0,
    yCm: 0,
    zCm: index * 60,
    widthCm: 40,
    heightCm: 30,
    lengthCm: 60,
    rotationCode: "XYZ",
    loadingSequence: index,
  };
}

const VIEW: LoadPlanVisualization = {
  truck: TRUCK,
  items: [item(1), item(2), item(3)],
  unloadedItems: [],
};

const PLAN = {
  id: "lp1",
  occupancyPercent: 42.5,
  totalWeightKg: 1230,
  loadedCount: 3,
  unloadedCount: 0,
} as unknown as LoadPlan;

/** Props da última renderização da cena. */
function ultimaCena() {
  return cenaProps[cenaProps.length - 1];
}

async function abrirPassoAPasso() {
  render(<LoadViewer planId="lp1" plan={PLAN} />);
  await screen.findByTestId("cena");
  fireEvent.click(screen.getByRole("button", { name: "Ver carregamento" }));
}

describe("LoadViewer — passo a passo", () => {
  beforeEach(() => {
    cenaProps.length = 0;
    vi.mocked(getLoadPlanVisualization).mockResolvedValue(VIEW);
  });

  it("mostra os indicadores que o backend calculou, sem recalcular", async () => {
    render(<LoadViewer planId="lp1" plan={PLAN} />);
    await screen.findByTestId("cena");

    expect(screen.getByText("42.5")).toBeInTheDocument();
    // 1230 kg publicados como 1.23 t
    expect(screen.getByText("1.23")).toBeInTheDocument();
  });

  it("começa no primeiro volume e anuncia o passo", async () => {
    await abrirPassoAPasso();

    // Escopado no passo a passo: o código também aparece no painel de detalhe,
    // porque avançar o passo seleciona o volume.
    const passo = document.querySelector(".viewer-stepper");
    expect(passo).not.toBeNull();
    expect(within(passo as HTMLElement).getByText("de 3")).toBeInTheDocument();
    expect(within(passo as HTMLElement).getByText("COD-1")).toBeInTheDocument();
  });

  it("inclui na cena o volume que está ENTRANDO, senão ele não teria como deslizar", async () => {
    await abrirPassoAPasso();

    const { visibleIds, enteringId } = ultimaCena();
    expect(enteringId).toBe("v1");
    expect(visibleIds?.has("v1")).toBe(true);
    expect(visibleIds?.has("v2")).toBe(false);
  });

  it("avança e volta com as setas do teclado", async () => {
    await abrirPassoAPasso();

    fireEvent.keyDown(window, { key: "ArrowRight" });
    await waitFor(() => expect(ultimaCena().enteringId).toBe("v2"));

    fireEvent.keyDown(window, { key: "ArrowRight" });
    await waitFor(() => expect(ultimaCena().enteringId).toBe("v3"));

    fireEvent.keyDown(window, { key: "ArrowLeft" });
    await waitFor(() => expect(ultimaCena().enteringId).toBe("v2"));
  });

  it("não passa das pontas da sequência", async () => {
    await abrirPassoAPasso();

    fireEvent.keyDown(window, { key: "ArrowLeft" });
    await waitFor(() => expect(ultimaCena().enteringId).toBe("v1"));

    for (let i = 0; i < 6; i += 1) fireEvent.keyDown(window, { key: "ArrowRight" });
    await waitFor(() => expect(ultimaCena().enteringId).toBe("v3"));
  });

  it("seleciona o volume do passo, para o painel de detalhe acompanhar", async () => {
    await abrirPassoAPasso();

    await waitFor(() => expect(ultimaCena().selectedId).toBe("v1"));
    fireEvent.keyDown(window, { key: "ArrowRight" });
    await waitFor(() => expect(ultimaCena().selectedId).toBe("v2"));
  });

  it("as setas só agem com o passo a passo aberto", async () => {
    render(<LoadViewer planId="lp1" plan={PLAN} />);
    await screen.findByTestId("cena");

    fireEvent.keyDown(window, { key: "ArrowRight" });

    // fora do passo a passo a cena mostra a carga inteira
    expect(ultimaCena().visibleIds).toBeNull();
    expect(ultimaCena().enteringId).toBeNull();
  });

  it("volta para a carga completa", async () => {
    await abrirPassoAPasso();
    fireEvent.click(screen.getByRole("button", { name: "Ver carga completa" }));

    await waitFor(() => expect(ultimaCena().visibleIds).toBeNull());
  });
});
