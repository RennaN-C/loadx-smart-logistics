import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { ImportPreviewTable } from "./ImportPreviewTable";
import { ImportErrors } from "./ImportErrors";
it("pagina prévia grande sem perder posição da linha", () => {
  render(<ImportPreviewTable preview={{ entity_type: "products", sha256: "hash", row_count: 25, valid_count: 25, can_confirm: true, errors: [], rows: Array.from({ length: 25 }, (_, i) => ({ line: i + 2, data: { name: `Registro ${i}` } })) }} />);
  expect(screen.queryByText("Registro 24")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Próxima/ }));
  expect(screen.getByText("Registro 24")).toBeInTheDocument();
});
it("pagina erros e identifica problema de arquivo inteiro", () => {
  render(<ImportErrors errors={Array.from({ length: 22 }, (_, line) => ({ line, field: "code", code: "DUPLICATE", message: `Problema ${line}` }))} />);
  expect(screen.getByText(/Arquivo · code: Problema 0/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Próxima/ }));
  expect(screen.getByText(/Linha 21 · code: Problema 21/)).toBeInTheDocument();
});
