import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TruckSchematic } from "./TruckSchematic";
import { computeRearLayout, computeSideLayout } from "./truckGeometry";

const MEDIUM = { widthCm: 240, heightCm: 260, lengthCm: 600 };

describe("computeSideLayout", () => {
  it("desenha o baú proporcional ao comprimento informado", () => {
    const short = computeSideLayout({ ...MEDIUM, lengthCm: 400 }, "detailed");
    const long = computeSideLayout({ ...MEDIUM, lengthCm: 800 }, "detailed");

    expect(long.boxWidth).toBeCloseTo(short.boxWidth * 2, 5);
  });

  it("desenha o baú proporcional à altura informada", () => {
    const low = computeSideLayout({ ...MEDIUM, heightCm: 200 }, "detailed");
    const tall = computeSideLayout({ ...MEDIUM, heightCm: 300 }, "detailed");

    expect(tall.boxHeight).toBeCloseTo(low.boxHeight * 1.5, 5);
  });

  it("mantém o piso do baú acima do topo dos pneus", () => {
    const layout = computeSideLayout(MEDIUM, "detailed");

    expect(layout.deckY).toBeLessThan(layout.groundY - layout.wheelRadius * 2);
  });

  it("posiciona o eixo traseiro na metade de trás do baú", () => {
    const layout = computeSideLayout(MEDIUM, "detailed");

    expect(layout.rearAxleX).toBeGreaterThan(layout.boxLeft + layout.boxWidth / 2);
    expect(layout.rearAxleX).toBeLessThan(layout.boxRight);
  });

  it("reduz a escala para não estourar a viewBox com medidas extremas", () => {
    const layout = computeSideLayout({ widthCm: 300, heightCm: 500, lengthCm: 2000 }, "detailed");

    expect(layout.boxRight).toBeLessThanOrEqual(layout.viewWidth);
    expect(layout.boxTop).toBeGreaterThan(0);
  });
});

describe("computeRearLayout", () => {
  it("desenha a traseira proporcional à largura informada", () => {
    const narrow = computeRearLayout({ ...MEDIUM, widthCm: 250 }, "detailed");
    const wide = computeRearLayout({ ...MEDIUM, widthCm: 300 }, "detailed");

    expect(wide.boxWidth).toBeCloseTo(narrow.boxWidth * 1.2, 5);
  });

  it("aplica um tamanho mínimo para baús muito estreitos continuarem legíveis", () => {
    const tiny = computeRearLayout({ ...MEDIUM, widthCm: 20 }, "detailed");

    expect(tiny.boxWidth).toBe(50);
  });

  it("centraliza o baú na viewBox", () => {
    const layout = computeRearLayout(MEDIUM, "detailed");

    expect(layout.boxLeft).toBeCloseTo(layout.viewWidth - layout.boxRight, 5);
  });
});

describe("TruckSchematic", () => {
  it("mostra as cotas na variante detalhada", () => {
    render(<TruckSchematic dimensions={MEDIUM} view="side" variant="detailed" />);

    expect(screen.getByText("600 cm")).toBeInTheDocument();
    expect(screen.getByText("260 cm")).toBeInTheDocument();
    expect(screen.getByText("VISTA LATERAL")).toBeInTheDocument();
  });

  it("omite as cotas na variante de card", () => {
    render(<TruckSchematic dimensions={MEDIUM} view="side" variant="card" />);

    expect(screen.queryByText("600 cm")).not.toBeInTheDocument();
  });
});
