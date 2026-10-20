import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { listLoadPlans } from "../api/loadPlansApi";
import type { LoadPlanListItem } from "../types";
import { PlanHistory } from "./PlanHistory";

vi.mock("../api/loadPlansApi");
const item: LoadPlanListItem = {
  id: "abcd1234-plan", truckId: "t1", truckPlate: "ABC1D23", truckModel: "Baú com identificação extensa",
  status: "CALCULATED", createdAt: "2026-10-12T12:00:00Z", recalculatedFromId: null,
  loadedCount: 10, unloadedCount: 1, occupancyPercent: 21.5, totalWeightKg: 120, orderCount: 2,
};
function setup(path = "/planning", checker = false) {
  return render(<MemoryRouter initialEntries={[path]}><Link to="/products">Produtos</Link><Link to="/planning">Planejamento de carga</Link><Routes>
    <Route path="/planning" element={<PlanHistory checker={checker} />} />
    <Route path="/planning/:id" element={<div>Detalhe persistido</div>} />
    <Route path="/products" element={<div>Cadastro de produtos</div>} />
  </Routes></MemoryRouter>);
}
describe("PlanHistory", () => {
  beforeEach(() => { vi.resetAllMocks(); vi.mocked(listLoadPlans).mockResolvedValue(makePage([item])); });
  it("reencontra o plano depois de sair para Produtos, sem calcular", async () => {
    setup();
    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Produtos" }));
    expect(screen.getByText("Cadastro de produtos")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Planejamento de carga" }));
    fireEvent.click(await screen.findByRole("link", { name: "Abrir plano abcd1234" }));
    expect(screen.getByText("Detalhe persistido")).toBeInTheDocument();
    expect(listLoadPlans).toHaveBeenCalledTimes(2);
  });
  it("restaura pagina, filtro e ordenacao da URL apos remontar", async () => {
    const view = setup("/planning?page=2&status=REJECTED&sort=asc");
    await screen.findByText("ABC1D23");
    expect(listLoadPlans).toHaveBeenLastCalledWith({ page: 2, status: "REJECTED", sortOrder: "asc" });
    view.unmount();
    setup("/planning?page=2&status=REJECTED&sort=asc");
    await screen.findByText("ABC1D23");
    expect(listLoadPlans).toHaveBeenCalledTimes(2);
  });
  it("pagina no servidor e reinicia a pagina quando muda o filtro", async () => {
    vi.mocked(listLoadPlans).mockResolvedValue({ ...makePage([item]), totalPages: 3, total: 45 });
    setup(); await screen.findByText("ABC1D23");
    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(listLoadPlans).toHaveBeenLastCalledWith({ page: 2, status: undefined, sortOrder: "desc" }));
    await screen.findByText("ABC1D23");
    fireEvent.change(screen.getByLabelText("Situação"), { target: { value: "APPROVED" } });
    await waitFor(() => expect(listLoadPlans).toHaveBeenLastCalledWith({ page: 1, status: "APPROVED", sortOrder: "desc" }));
  });
  it("mostra falha e tenta novamente sem converter erro em vazio", async () => {
    vi.mocked(listLoadPlans).mockRejectedValueOnce(new Error("API indisponível"));
    setup(); expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível");
    expect(screen.queryByText("Nenhum plano nesta consulta")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
  });
  it("apresenta vazio e leitura limitada do conferente", async () => {
    vi.mocked(listLoadPlans).mockResolvedValue(makePage([]));
    setup("/planning", true);
    expect(await screen.findByText("Nenhum plano nesta consulta")).toBeInTheDocument();
    expect(screen.getByText("Você consulta somente planos aprovados.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Situação")).not.toBeInTheDocument();
  });
  it("ignora resposta tardia da pagina anterior", async () => {
    let resolve!: (value: ReturnType<typeof makePage<LoadPlanListItem>>) => void;
    vi.mocked(listLoadPlans).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    setup(); fireEvent.change(screen.getByLabelText("Situação"), { target: { value: "APPROVED" } });
    await screen.findByText("ABC1D23");
    resolve(makePage([{ ...item, truckPlate: "STALE" }]));
    await waitFor(() => expect(screen.queryByText("STALE")).not.toBeInTheDocument());
  });
});


it("filtra planos pelo caminhao identificado na linha e permite limpar", async () => {
  vi.mocked(listLoadPlans).mockResolvedValue(makePage([item]));
  setup();
  fireEvent.click(await screen.findByRole("link", { name: "Filtrar planos do caminhão ABC1D23" }));
  await waitFor(() => expect(listLoadPlans).toHaveBeenLastCalledWith({ page: 1, status: undefined, sortOrder: "desc", truckId: "t1" }));
  fireEvent.click(await screen.findByRole("button", { name: "Limpar filtro de caminhão" }));
  await waitFor(() => expect(listLoadPlans).toHaveBeenLastCalledWith({ page: 1, status: undefined, sortOrder: "desc" }));
});


it("conferente nao recebe link de origem cuja aprovacao nao foi confirmada", async () => {
  vi.mocked(listLoadPlans).mockResolvedValue(makePage([{ ...item, status: "APPROVED", recalculatedFromId: "p0" }]));
  setup("/planning", true);
  await screen.findByRole("link", { name: "Abrir plano abcd1234" });
  expect(screen.queryByRole("link", { name: "Ver plano de origem" })).not.toBeInTheDocument();
});


it("abre agregado persistido ao reencontrar plano de uma distribuição", async () => {
  vi.mocked(listLoadPlans).mockResolvedValue(makePage([{ ...item, distributionId: "distribution-1" }]));
  setup();
  const link = await screen.findByRole("link", { name: "Abrir plano abcd1234" });
  expect(link).toHaveAttribute("href", "/planning/distributions/distribution-1");
  expect(link).toHaveTextContent("Abrir distribuição");
});
