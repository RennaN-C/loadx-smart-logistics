import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { BrandPanel } from "./BrandPanel";

it("apresenta a marca sem inventar ambiente ou versao do sistema", () => {
  render(<BrandPanel />);
  expect(screen.getByRole("heading", { name: /Logística inteligente.*Operação conectada/ })).toBeInTheDocument();
  expect(screen.getByText("LOADX", { exact: true })).toBeInTheDocument();
  expect(screen.getByText("LOADX · LOGÍSTICA INTELIGENTE")).toBeInTheDocument();
  expect(screen.queryByText(/AMBIENTE LOCAL|V0\.1/)).not.toBeInTheDocument();
});

it("permite pausar e retomar os efeitos decorativos sem alterar o acesso", () => {
  render(<BrandPanel />);
  const pause = screen.getByRole("button", { name: "Pausar efeitos" });
  expect(pause).toHaveAttribute("aria-pressed", "false");
  fireEvent.click(pause);
  expect(screen.getByRole("button", { name: "Ativar efeitos" })).toHaveAttribute("aria-pressed", "true");
  expect(pause.closest("aside")).toHaveClass("is-motion-paused");
  fireEvent.click(screen.getByRole("button", { name: "Ativar efeitos" }));
  expect(screen.getByRole("button", { name: "Pausar efeitos" })).toHaveAttribute("aria-pressed", "false");
  expect(pause.closest("aside")).not.toHaveClass("is-motion-paused");
});
