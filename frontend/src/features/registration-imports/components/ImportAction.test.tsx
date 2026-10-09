import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ImportAction } from "./ImportAction";
vi.mock("./ImportPanel", () => ({ ImportPanel: ({ entity }: { entity: string }) => <p>Arquivo de {entity}</p> }));
it.each([["customers", "clientes"], ["products", "produtos"], ["trucks", "caminhões"], ["drivers", "motoristas"]] as const)("abre contexto de %s sob demanda", (entity, label) => {
  render(<ImportAction entity={entity} onImported={vi.fn()} />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: `Importar ${label}` }));
  expect(screen.getByText(`Arquivo de ${entity}`)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
