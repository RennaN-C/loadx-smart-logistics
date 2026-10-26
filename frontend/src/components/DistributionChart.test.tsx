import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { DistributionChart } from "./DistributionChart";

it.each(["ring", "columns"] as const)("exibe contagens reais e legenda acessível no gráfico %s", (variant) => {
  render(<DistributionChart title="Viagens" total={4} entries={[{ label: "Em rota", value: 3 }, { label: "Finalizadas", value: 1 }]} variant={variant} />);
  expect(screen.getByRole("img", { name: "Viagens: 4 registros" })).toBeInTheDocument();
  expect(screen.getByRole("list")).toHaveTextContent("Em rota3Finalizadas1");
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});

it("mostra o estado vazio sem geometria inválida", () => {
  const { container } = render(<DistributionChart title="Viagens" total={0} entries={[{ label: "Em rota", value: 0 }]} />);
  expect(screen.getByText("Sem registros nesta consulta.")).toBeInTheDocument();
  expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
});
