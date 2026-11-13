import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { BrandPanel } from "./BrandPanel";

it("mantém os textos e diferenciais em HTML, separados do cenário decorativo", () => {
  render(<BrandPanel />);
  expect(screen.getByRole("heading", { name: /Planejamento inteligente para.*uma logística mais eficiente/ })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "LoadX Smart Logistics" })).toBeInTheDocument();
  expect(screen.getAllByRole("listitem")).toHaveLength(3);
  expect(screen.getByText(/Conferência/)).toBeInTheDocument();
  expect(screen.getByText(/Acompanhamento/)).toBeInTheDocument();
  expect(screen.queryByText(/Otimização de Rotas/)).not.toBeInTheDocument();
});

it("usa marca SVG e cenário sem substituir a interface por fotografia", () => {
  render(<BrandPanel />);
  const scene = document.querySelector(".login-scene-photo");
  expect(scene).toHaveAttribute("src", "/images/login-scene-hd.webp");
  expect(scene).toHaveAttribute("alt", "");
  expect(scene).toHaveAttribute("aria-hidden", "true");
  expect(document.querySelector(".login-brand-symbol")).toHaveAttribute("src", "/branding/loadx-login-mark.svg");
  expect(document.querySelector(".login-globe")).toHaveAttribute("src", "/images/login-globe.svg");
  expect(document.querySelector(".login-brand-live")).toBeInTheDocument();
});
