import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { BrandPanel } from "./BrandPanel";

it("apresenta a marca sem inventar ambiente ou versao do sistema", () => {
  render(<BrandPanel />);
  expect(screen.getByRole("heading", { name: /Logística inteligente.*Operação conectada/ })).toBeInTheDocument();
  expect(screen.getByText("LOADX", { exact: true })).toBeInTheDocument();
  expect(screen.getByText("LOADX · LOGÍSTICA INTELIGENTE")).toBeInTheDocument();
  expect(screen.queryByText(/AMBIENTE LOCAL|V0\.1/)).not.toBeInTheDocument();
});
