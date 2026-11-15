import { render } from "@testing-library/react";
import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CameraControls } from "./CameraControls";

const dispose = vi.fn();
const update = vi.fn();
const targetSet = vi.fn();
const construir = vi.fn();
const cameraSet = vi.fn();
const invalidate = vi.fn();
const addEventListener = vi.fn();
const removeEventListener = vi.fn();

vi.mock("@react-three/fiber", () => {
  // Estado FIXO: no R3F real `state.camera` e `state.gl` mantêm a referência
  // entre renders. Recriar aqui faria o useMemo reconstruir os controles e
  // mascararia justamente o que estes testes existem para vigiar.
  const state = {
    camera: { id: "camera", position: { set: (...args: unknown[]) => cameraSet(...args) } },
    gl: { domElement: { id: "canvas" } },
    invalidate: (...args: unknown[]) => invalidate(...args),
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
    addEventListener = addEventListener;
    removeEventListener = removeEventListener;
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
    expect(removeEventListener).toHaveBeenCalledWith("change", expect.any(Function));
  });

  it("recentraliza a vista atual mesmo quando as coordenadas não mudaram", () => {
    const { rerender } = render(<CameraControls target={[1, 2, 3]} position={[9, 8, 7]} resetToken={0} />);
    cameraSet.mockClear();
    rerender(<CameraControls target={[1, 2, 3]} position={[9, 8, 7]} resetToken={1} />);
    expect(cameraSet).toHaveBeenCalledWith(9, 8, 7);
    expect(construir).toHaveBeenCalledOnce();
    expect(dispose).not.toHaveBeenCalled();
  });

  it("agenda renderização quando OrbitControls informa movimento", () => {
    render(<CameraControls target={[1, 2, 3]} position={[9, 8, 7]} />);
    expect(addEventListener).toHaveBeenCalledWith("change", expect.any(Function));
    const callback = addEventListener.mock.calls[0][1] as () => void;
    invalidate.mockClear();
    callback();
    expect(invalidate).toHaveBeenCalledOnce();
  });

  it("reconecta controles no ciclo de verificação do StrictMode", () => {
    const { unmount } = render(<StrictMode><CameraControls target={[1, 2, 3]} position={[9, 8, 7]} /></StrictMode>);
    expect(construir).toHaveBeenCalledTimes(2);
    expect(dispose).toHaveBeenCalledTimes(1);
    expect(addEventListener).toHaveBeenCalledTimes(2);
    unmount();
    expect(dispose).toHaveBeenCalledTimes(2);
    expect(removeEventListener).toHaveBeenCalledTimes(2);
  });
});
