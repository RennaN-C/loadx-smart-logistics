import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TruckSchematic } from "./TruckSchematic";

const MEDIUM = { widthCm: 240, heightCm: 260, lengthCm: 600 };

describe("TruckSchematic", () => {
  it("mostra comprimento e altura na vista lateral detalhada", () => {
    render(<TruckSchematic dimensions={MEDIUM} view="side" variant="detailed" />);

    expect(screen.getByText("600 cm")).toBeInTheDocument();
    expect(screen.getByText("COMPRIMENTO")).toBeInTheDocument();
    expect(screen.getByText("260 cm")).toBeInTheDocument();
    expect(screen.getByText("ALTURA INTERNA")).toBeInTheDocument();
  });

  it("mostra a largura na vista traseira detalhada", () => {
    render(<TruckSchematic dimensions={MEDIUM} view="rear" variant="detailed" />);

    expect(screen.getByText("240 cm")).toBeInTheDocument();
    expect(screen.getByText("LARGURA")).toBeInTheDocument();
  });

  it("mostra um traço no lugar de '0 cm' antes de a medida ser digitada", () => {
    render(<TruckSchematic dimensions={{ widthCm: 0, heightCm: 0, lengthCm: 0 }} view="side" variant="detailed" />);

    expect(screen.queryByText("0 cm")).not.toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
  });

  it("omite as cotas na variante de card", () => {
    render(<TruckSchematic dimensions={MEDIUM} view="side" variant="card" />);

    expect(screen.queryByText("600 cm")).not.toBeInTheDocument();
    expect(screen.queryByText("COMPRIMENTO")).not.toBeInTheDocument();
  });

  it("usa imagens diferentes para lateral e traseira, marcadas como decorativas", () => {
    const { container: side } = render(<TruckSchematic dimensions={MEDIUM} view="side" variant="card" />);
    const sideImg = side.querySelector("img");
    const { container: rear } = render(<TruckSchematic dimensions={MEDIUM} view="rear" variant="card" />);
    const rearImg = rear.querySelector("img");

    expect(sideImg?.getAttribute("src")).toBe("/trucks/truck-side.png");
    expect(rearImg?.getAttribute("src")).toBe("/trucks/truck-rear.png");
    // alt vazio: a informação está nas cotas, que são texto
    expect(sideImg?.getAttribute("alt")).toBe("");
  });
});
