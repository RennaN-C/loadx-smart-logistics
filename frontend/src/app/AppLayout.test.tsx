import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppLayout } from "./AppLayout";

describe("AppLayout", () => {
  it("renderiza o cabeçalho da LoadX e o conteúdo da rota filha", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<p>conteudo da rota</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("LOADX")).toBeInTheDocument();
    expect(screen.getByText("conteudo da rota")).toBeInTheDocument();
  });
});
