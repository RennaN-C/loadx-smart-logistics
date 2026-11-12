import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { BrandPanel } from "./BrandPanel";

it("apresenta a marca sem inventar ambiente ou versao do sistema", () => {
  render(<BrandPanel />);
  expect(screen.getByRole("heading", { name: /Planejamento inteligente para.*uma logística mais eficiente/ })).toBeInTheDocument();
  expect(screen.getByText("LOADX", { exact: true })).toBeInTheDocument();
  expect(document.querySelector(".login-wordmark .loadx-brand-mark")).toHaveAttribute("src", "/branding/loadx-mark-128.png");
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


it("desenha três rotas locais decorativas com sinais e conexões", () => {
  render(<BrandPanel />);
  const routes = document.querySelector(".login-routes");
  expect(routes).toHaveAttribute("aria-hidden", "true");
  expect(routes).toHaveAttribute("focusable", "false");
  expect(routes?.querySelectorAll(".login-route-signal")).toHaveLength(3);
  expect(routes?.querySelectorAll(".login-route-track")).toHaveLength(3);
  expect(routes?.querySelectorAll(".login-route-hub")).toHaveLength(3);
  expect(routes?.querySelectorAll(".login-route-core")).toHaveLength(3);
  expect(screen.queryByText(/rotas|rentabilidade/i)).not.toBeInTheDocument();
});


it("utiliza o cenário cinematográfico local sem texto ou autenticação embutidos", () => {
  render(<BrandPanel />);
  const artwork = document.querySelector(".login-hero-photo");
  expect(artwork).toHaveAttribute("src", "/images/login-cinematic-scene-hd.webp");
  expect(artwork).toHaveAttribute("width", "1800");
  expect(artwork).toHaveAttribute("height", "2000");
  expect(artwork).toHaveAttribute("aria-hidden", "true");
  expect(artwork).toHaveAttribute("alt", "");
});
