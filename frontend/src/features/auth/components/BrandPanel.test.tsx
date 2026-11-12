import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { BrandPanel } from "./BrandPanel";

it("preserva a identidade real do LoadX e o conteúdo semântico para mobile e acessibilidade", () => {
  render(<BrandPanel />);
  expect(screen.getByRole("heading", { name: /Planejamento inteligente para.*uma logística mais eficiente/ })).toBeInTheDocument();
  expect(screen.getByText("LOADX", { exact: true })).toBeInTheDocument();
  expect(document.querySelector(".login-wordmark .loadx-brand-mark")).toHaveAttribute("src", "/branding/loadx-mark-128.png");
  expect(screen.getByText("LOADX · LOGÍSTICA INTELIGENTE")).toBeInTheDocument();
  expect(screen.queryByText(/AMBIENTE LOCAL|V0\\.1/)).not.toBeInTheDocument();
});

it("usa somente a arte aprovada no desktop sem substituir os controles de login", () => {
  render(<BrandPanel />);
  const image = document.querySelector(".login-reference-art");
  expect(image).toHaveAttribute("src", "/images/login-reference-left.avif");
  expect(image).toHaveAttribute("width", "1006");
  expect(image).toHaveAttribute("height", "941");
  expect(image).toHaveAttribute("aria-hidden", "true");
  expect(image).toHaveAttribute("alt", "");
  expect(document.querySelector(".login-brand-live")).toBeInTheDocument();
});

it("remove as camadas artificiais, linhas cruzando o caminhão e botões de efeitos", () => {
  render(<BrandPanel />);
  expect(document.querySelector(".login-routes")).not.toBeInTheDocument();
  expect(document.querySelector(".login-atmosphere")).not.toBeInTheDocument();
  expect(document.querySelector(".login-world-map")).not.toBeInTheDocument();
  expect(document.querySelector(".login-map-veil")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /pausar efeitos|ativar efeitos/i })).not.toBeInTheDocument();
});
