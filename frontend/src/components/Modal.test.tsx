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

describe("Regressões de foco dos diálogos", () => {
  it("prende Tab e Shift+Tab no diálogo e restaura foco e rolagem ao fechar", () => {
    const trigger = document.createElement("button");
    document.body.append(trigger); trigger.focus();
    const previous = document.body.style.overflow;
    const view = render(<Modal title="Editar" onClose={vi.fn()}><input aria-label="Nome" /><button>Salvar</button></Modal>);
    expect(screen.getByRole("textbox")).toHaveFocus();
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(screen.getByRole("button", { name: "Salvar" })).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(screen.getByRole("textbox")).toHaveFocus();
    view.unmount();
    expect(trigger).toHaveFocus();
    expect(document.body.style.overflow).toBe(previous);
    trigger.remove();
  });

  it("Escape fecha apenas o diálogo superior e desmontar todos libera rolagem", () => {
    const parent = vi.fn(); const child = vi.fn();
    const before = document.body.style.overflow;
    const view = render(<Modal title="Pai" onClose={parent}><Modal title="Filho" onClose={child}><button>Confirmar</button></Modal></Modal>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(child).toHaveBeenCalledOnce();
    expect(parent).not.toHaveBeenCalled();
    view.unmount();
    expect(document.body.style.overflow).toBe(before);
  });

  it("diálogo sem campos recebe foco e Tab não escapa", () => {
    render(<Modal title="Informação" onClose={vi.fn()}><p>Conteúdo</p></Modal>);
    expect(screen.getByRole("dialog")).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(screen.getByRole("dialog")).toHaveFocus();
  });
});
