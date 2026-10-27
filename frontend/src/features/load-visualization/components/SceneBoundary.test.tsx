import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { SceneBoundary } from "./SceneBoundary";

it("falha WebGL mantém orientação amigável e permite reabrir a cena", () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
  const expectedError = (event: ErrorEvent) => { if (event.message.includes("private WebGL trace")) event.preventDefault(); };
  window.addEventListener("error", expectedError);
  let fail = true;
  function Scene() { if (fail) throw new Error("private WebGL trace"); return <div>Cena recuperada</div>; }
  try {
    render(<SceneBoundary><Scene /></SceneBoundary>);
    expect(screen.getByRole("alert")).toHaveTextContent("tabela de volumes");
    expect(screen.getByRole("alert")).not.toHaveTextContent("private");
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Tentar abrir o 3D novamente" }));
    expect(screen.getByText("Cena recuperada")).toBeInTheDocument();
  } finally { window.removeEventListener("error", expectedError); consoleError.mockRestore(); }
});
