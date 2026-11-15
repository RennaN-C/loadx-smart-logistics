import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  internalVolumeCm3: 37_440_000,
  usedVolumeCm3: 2_000_000,
  status: "CALCULATED",
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


it("oferece nova consulta da cena após falha, sem calcular", async () => {
  vi.mocked(getLoadPlanVisualization).mockReset().mockRejectedValueOnce(new Error("Falha temporária")).mockResolvedValue(VIEW);
  render(<LoadViewer planId="lp1" plan={PLAN} />);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Tentar carregar visualização novamente" }));
  expect(await screen.findByTestId("cena")).toBeInTheDocument();
  expect(getLoadPlanVisualization).toHaveBeenCalledTimes(2);
});


it("remonta a cena ao mudar de plano e não apresenta volumes anteriores", async () => {
  vi.mocked(getLoadPlanVisualization).mockReset();
  let finish!: (value: LoadPlanVisualization) => void;
  vi.mocked(getLoadPlanVisualization).mockReturnValueOnce(new Promise((resolve) => { finish = resolve; })).mockResolvedValueOnce(VIEW);
  const view = render(<LoadViewer planId="lp1" plan={PLAN} />);
  // The first deferred response belongs to the old vehicle and must be ignored.
  view.rerender(<LoadViewer planId="lp2" plan={{ ...PLAN, id: "lp2" }} />);
  await screen.findByTestId("cena");
  await act(async () => finish({ ...VIEW, truck: { ...TRUCK, plate: "OLD0X00" } }));
  expect(ultimaCena().truck.plate).toBe(TRUCK.plate);
  expect(ultimaCena().items.map((volume) => volume.id)).toEqual(VIEW.items.map((volume) => volume.id));
  expect(getLoadPlanVisualization).toHaveBeenNthCalledWith(2, "lp2");
});


it("expande a mesma cena, preserva câmera e devolve foco após Escape", async () => {
  vi.mocked(getLoadPlanVisualization).mockReset().mockResolvedValue(VIEW);
  render(<LoadViewer planId="lp1" plan={PLAN} />);
  const scene = await screen.findByTestId("cena");
  fireEvent.click(screen.getByRole("button", { name: "Topo" }));
  expect(ultimaCena().view).toBe("top");
  const expand = screen.getByRole("button", { name: "Expandir visualização 3D" });
  expand.focus();
  fireEvent.click(expand);
  const dialog = screen.getByRole("dialog", { name: "Visualização 3D da carga" });
  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(document.body.style.overflow).toBe("hidden");
  expect(screen.getByTestId("cena")).toBe(scene);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByTestId("cena")).toBe(scene);
  expect(expand).toHaveFocus();
  expect(document.body.style.overflow).not.toBe("hidden");
  expect(getLoadPlanVisualization).toHaveBeenCalledTimes(1);
  expect(ultimaCena().view).toBe("top");
});


it("retira a geometria antiga enquanto o próximo caminhão carrega, mesmo sem key no consumidor", async () => {
  vi.mocked(getLoadPlanVisualization).mockReset();
  let finish!: (value: LoadPlanVisualization) => void;
  vi.mocked(getLoadPlanVisualization).mockResolvedValueOnce(VIEW).mockReturnValueOnce(new Promise(resolve => { finish = resolve; }));
  const component = render(<LoadViewer planId="lp1" plan={PLAN} />);
  await screen.findByTestId("cena");
  component.rerender(<LoadViewer planId="lp2" plan={{ ...PLAN, id: "lp2" }} />);
  expect(screen.queryByTestId("cena")).not.toBeInTheDocument();
  const replacement = { ...VIEW, truck: { ...TRUCK, widthCm: 100 }, items: [item(7)] };
  await act(async () => { finish(replacement); });
  await screen.findByTestId("cena");
  expect(ultimaCena().truck.widthCm).toBe(100);
  expect(ultimaCena().items.map(volume => volume.id)).toEqual(["v7"]);
});

describe("professional inspection workspace", () => {
  beforeEach(() => {
    cenaProps.length = 0;
    vi.mocked(getLoadPlanVisualization).mockReset().mockResolvedValue(VIEW);
  });

  it("selects and clears a volume using the accessible keyboard control", async () => {
    render(<LoadViewer planId="lp1" plan={PLAN} />);
    const select = await screen.findByRole("combobox", { name: "Selecionar volume" });
    fireEvent.change(select, { target: { value: "v2" } });
    expect(ultimaCena().selectedId).toBe("v2");
    expect(screen.getByRole("region", { name: "Detalhes do volume selecionado" })).toHaveTextContent("COD-2");
    expect(screen.getByRole("region", { name: "Detalhes do volume selecionado" })).toHaveTextContent("40×30×60 cm");
    fireEvent.click(screen.getByRole("button", { name: "Limpar seleção" }));
    expect(select).toHaveValue("");
    expect(ultimaCena().selectedId).toBeNull();
    expect(screen.queryByRole("region", { name: "Detalhes do volume selecionado" })).not.toBeInTheDocument();
  });

  it("reframes the current camera without refetching or losing the selected volume", async () => {
    render(<LoadViewer planId="lp1" plan={PLAN} />);
    fireEvent.change(await screen.findByLabelText("Selecionar volume"), { target: { value: "v3" } });
    fireEvent.click(screen.getByRole("button", { name: "Frontal" }));
    const previousToken = ultimaCena().resetToken;
    fireEvent.click(screen.getByRole("button", { name: "Centralizar câmera" }));
    expect(ultimaCena().view).toBe("front");
    expect(ultimaCena().resetToken).toBe((previousToken ?? 0) + 1);
    expect(ultimaCena().selectedId).toBe("v3");
    expect(getLoadPlanVisualization).toHaveBeenCalledTimes(1);
  });

  it("displays truck capacity and published metrics without deriving a new occupancy", async () => {
    render(<LoadViewer planId="lp1" plan={PLAN} />);
    await screen.findByTestId("cena");
    const capacity = screen.getByRole("complementary", { name: "Informações da carga" });
    expect(capacity).toHaveTextContent("8.000 kg");
    expect(capacity).toHaveTextContent("1.230 kg");
    expect(capacity).toHaveTextContent("6.770 kg");
    expect(capacity).toHaveTextContent("37,44 m³");
    expect(capacity).toHaveTextContent("35,44 m³");
    // The deliberately distinct published occupancy must remain authoritative.
    expect(screen.getByRole("meter", { name: "Ocupação volumétrica" })).toHaveAttribute("value", "42.5");
  });

  it("supports 200 distinct volumes and preserves their API positions and dimensions", async () => {
    const volumes = Array.from({ length: 200 }, (_, index) => ({
      ...item(index + 1), volumeIndex: index + 1,
      xCm: (index % 5) * 40, yCm: Math.floor(index / 50) * 30,
      zCm: Math.floor((index % 50) / 5) * 60,
    }));
    vi.mocked(getLoadPlanVisualization).mockResolvedValue({ ...VIEW, items: volumes });
    render(<LoadViewer planId="lp1" plan={{ ...PLAN, loadedCount: 200 }} />);
    const select = await screen.findByRole("combobox", { name: "Selecionar volume" });
    expect(within(select).getAllByRole("option")).toHaveLength(201);
    fireEvent.change(select, { target: { value: "v200" } });
    expect(ultimaCena().selectedId).toBe("v200");
    expect(ultimaCena().items).toEqual(volumes);
    expect(screen.getByRole("region", { name: "Detalhes do volume selecionado" })).toHaveTextContent("COD-200");
  });

  it("keeps the selected detail synchronized during automatic playback", async () => {
    await abrirPassoAPasso();
    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole("button", { name: "Tocar" }));
      act(() => { vi.advanceTimersByTime(421); });
      expect(ultimaCena().selectedId).toBe("v2");
      expect(screen.getByRole("region", { name: "Detalhes do volume selecionado" })).toHaveTextContent("COD-2");
      act(() => { vi.advanceTimersByTime(840); });
      expect(ultimaCena().selectedId).toBe("v3");
      expect(screen.getByRole("button", { name: "Tocar" })).toBeInTheDocument();
    } finally { vi.useRealTimers(); }
  });

  it("does not steal arrow keys from the loading slider or volume selector", async () => {
    await abrirPassoAPasso();
    fireEvent.keyDown(screen.getByRole("slider", { name: "Passo do carregamento" }), { key: "ArrowRight" });
    expect(ultimaCena().enteringId).toBe("v1");
    fireEvent.keyDown(screen.getByLabelText("Selecionar volume"), { key: "ArrowRight" });
    expect(ultimaCena().enteringId).toBe("v1");
    fireEvent.keyDown(window, { key: "ArrowRight", ctrlKey: true });
    expect(ultimaCena().enteringId).toBe("v1");
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(ultimaCena().enteringId).toBe("v2");
  });

  it("shows the empty state without mounting a WebGL scene", async () => {
    vi.mocked(getLoadPlanVisualization).mockResolvedValue({ ...VIEW, items: [] });
    render(<LoadViewer planId="lp1" plan={{ ...PLAN, loadedCount: 0 }} />);
    expect(await screen.findByText(/Nenhum volume foi carregado neste plano/)).toBeInTheDocument();
    expect(screen.queryByTestId("cena")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Selecionar volume")).not.toBeInTheDocument();
  });
});
