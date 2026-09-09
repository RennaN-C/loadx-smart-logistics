import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CameraControls } from "./CameraControls";

const dispose = vi.fn();
const update = vi.fn();
const targetSet = vi.fn();
const construir = vi.fn();

vi.mock("@react-three/fiber", () => {
  // Estado FIXO: no R3F real `state.camera` e `state.gl` mantêm a referência
  // entre renders. Recriar aqui faria o useMemo reconstruir os controles e
  // mascararia justamente o que estes testes existem para vigiar.
  const state = {
    camera: { id: "camera", position: { set: () => undefined } },
    gl: { domElement: { id: "canvas" } },
  };

  return {
    useThree: (seletor: (state: unknown) => unknown) => seletor(state),
    useFrame: () => undefined,
  };
});

vi.mock("three/examples/jsm/controls/OrbitControls.js", () => ({
  OrbitControls: class {
    enableDamping = false;
    target = { set: targetSet };
    update = update;
    dispose = dispose;
    constructor(...args: unknown[]) {
      construir(...args);
    }
  },
}));

describe("CameraControls", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("aponta a câmera para o alvo recebido", () => {
    render(<CameraControls target={[1, 2, 3]} position={[9, 9, 9]} />);

    expect(construir).toHaveBeenCalledOnce();
    expect(targetSet).toHaveBeenCalledWith(1, 2, 3);
  });

  it("NÃO descarta os controles quando o alvo é remontado com os mesmos valores", () => {
    // Regressão: o alvo é um array literal, recriado a cada render de LoadScene.
    // Com o descarte amarrado a ele, um simples clique num volume derrubava os
    // ouvintes do canvas — a cena parava de girar e a roda rolava a página.
    const { rerender } = render(<CameraControls target={[1, 2, 3]} position={[9, 9, 9]} />);

    rerender(<CameraControls target={[1, 2, 3]} position={[9, 9, 9]} />);
    rerender(<CameraControls target={[1, 2, 3]} position={[9, 9, 9]} />);

    expect(dispose).not.toHaveBeenCalled();
    expect(construir).toHaveBeenCalledOnce();
  });

  it("reposiciona sem descartar quando o alvo muda de lugar de verdade", () => {
    // é o caso de ligar e desligar o caminhão: a carga sobe, o alvo sobe junto
    const { rerender } = render(<CameraControls target={[1, 2, 3]} position={[9, 9, 9]} />);
    targetSet.mockClear();

    rerender(<CameraControls target={[1, 3.15, 3]} position={[9, 9, 9]} />);

    expect(targetSet).toHaveBeenCalledWith(1, 3.15, 3);
    expect(dispose).not.toHaveBeenCalled();
  });

  it("descarta ao desmontar, para não vazar ouvinte no canvas", () => {
    const { unmount } = render(<CameraControls target={[1, 2, 3]} position={[9, 9, 9]} />);

    unmount();

    expect(dispose).toHaveBeenCalledOnce();
  });
});
