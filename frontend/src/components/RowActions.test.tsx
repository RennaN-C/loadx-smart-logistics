import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { RowActions } from "./RowActions";

it("revela ações sob demanda, executa o handler e fecha com Escape devolvendo o foco", () => {
  const edit = vi.fn();
  render(<RowActions label="Ações do registro"><button onClick={edit}>Editar</button></RowActions>);
  const trigger = screen.getByLabelText("Ações do registro");
  expect(screen.getByText("Editar")).not.toBeVisible();
  fireEvent.click(trigger);
  expect(screen.getByText("Editar")).toBeVisible();
  fireEvent.click(screen.getByText("Editar"));
  expect(edit).toHaveBeenCalledOnce();
  fireEvent.keyDown(screen.getByText("Editar"), { key: "Escape" });
  expect(screen.getByText("Editar")).not.toBeVisible();
  expect(trigger).toHaveFocus();
});
