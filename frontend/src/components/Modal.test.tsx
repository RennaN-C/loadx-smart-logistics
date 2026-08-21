import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Modal } from "./Modal";

describe("Modal", () => {
  it("renderiza título, subtítulo e conteúdo", () => {
    render(
      <Modal title="Novo caminhão" subtitle="Compartimento de carga" onClose={vi.fn()}>
        <p>conteudo do modal</p>
      </Modal>,
    );

    expect(screen.getByRole("dialog")).toHaveAccessibleName("Novo caminhão");
    expect(screen.getByText("Compartimento de carga")).toBeInTheDocument();
    expect(screen.getByText("conteudo do modal")).toBeInTheDocument();
  });

  it("fecha ao clicar fora do diálogo", () => {
    const onClose = vi.fn();
    render(
      <Modal title="Novo caminhão" onClose={onClose}>
        <p>conteudo</p>
      </Modal>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("fecha ao pressionar Escape", () => {
    const onClose = vi.fn();
    render(
      <Modal title="Novo caminhão" onClose={onClose}>
        <p>conteudo</p>
      </Modal>,
    );

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalledOnce();
  });
});
