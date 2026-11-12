import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { BrandPanel } from "./BrandPanel";

it("mantém marca oficial, título e funcionalidades exibidas sem inventar novas capacidades", () => {
  render(<BrandPanel />);
  expect(screen.getByRole("heading", { name: /Planejamento inteligente para.*uma logística mais eficiente/ })).toBeInTheDocument();
  expect(screen.getByText("LOADX", { exact: true })).toBeInTheDocument();
  expect(document.querySelector(".login-wordmark .loadx-brand-mark")).toHaveAttribute("src", "/branding/loadx-mark-128.png");
  expect(screen.getByText("LOADX · LOGÍSTICA INTELIGENTE")).toBeInTheDocument();
  expect(screen.queryByText(/AMBIENTE LOCAL|V0\\.1/)).not.toBeInTheDocument();
});

it("usa o asset HD real e deixa os textos e o login fora da fotografia", () => {
  render(<BrandPanel />);
  const image = document.querySelector(".login-hero-photo");
  expect(image).toHaveAttribute("src", "/images/login-cinematic-scene-hd.webp");
  expect(image).toHaveAttribute("width", "1800");
  expect(image).toHaveAttribute("height", "2000");
  expect(image).toHaveAttribute("alt", "");
  expect(image).toHaveAttribute("aria-hidden", "true");
});

it("não desenha rotas sobre o caminhão nem mostra botão de pausar efeitos", () => {
  render(<BrandPanel />);
  expect(document.querySelector(".login-routes")).not.toBeInTheDocument();
  expect(document.querySelector(".login-atmosphere")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /pausar efeitos|ativar efeitos/i })).not.toBeInTheDocument();
  const map = document.querySelector(".login-world-map");
  expect(map).toHaveAttribute("aria-hidden", "true");
  expect(map).toHaveAttribute("focusable", "false");
  expect(map?.querySelectorAll(".login-world-connections path")).toHaveLength(4);
  expect(map?.querySelectorAll(".login-world-points circle")).toHaveLength(5);
  expect(document.querySelector(".login-map-veil")).toHaveAttribute("aria-hidden", "true");
});
