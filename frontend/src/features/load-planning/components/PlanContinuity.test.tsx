import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getLoadPlanContinuity } from "../api/loadPlansApi";
import { PlanContinuity } from "./PlanContinuity";
vi.mock("../api/loadPlansApi");
vi.mock("../../deliveries/components/CreateTripAction", () => ({ CreateTripAction: ({ onExistingTrip }: { onExistingTrip: () => void }) => <button onClick={onExistingTrip}>Criar viagem</button> }));
vi.mock("../../loading-operation/components/StartLoadingAction", () => ({ StartLoadingAction: () => <button>Conferir carregamento</button> }));
function setup(canManage = true) { return render(<MemoryRouter><PlanContinuity planId="p1" canManage={canManage} /></MemoryRouter>); }
describe("PlanContinuity", () => {
  beforeEach(() => { vi.resetAllMocks(); });
  it("abre viagem e carregamento existentes, incluindo viagem concluida", async () => {
    vi.mocked(getLoadPlanContinuity).mockResolvedValue({ operational_ready: true, loading_session: { id: "s1", status: "FINISHED" }, trip: { id: "v1", status: "FINISHED" } });
    setup();
    expect(await screen.findByRole("link", { name: "Abrir viagem existente" })).toHaveAttribute("href", "/trips/v1");
    expect(screen.getByRole("link", { name: "Abrir carregamento existente" })).toHaveAttribute("href", "/loading/s1");
    expect(screen.queryByRole("button", { name: "Criar viagem" })).not.toBeInTheDocument();
  });
  it("falha fechada ate obter os vinculos e permite retry", async () => {
    vi.mocked(getLoadPlanContinuity).mockRejectedValueOnce(new Error("timeout")).mockResolvedValue({ operational_ready: true, loading_session: null, trip: null });
    setup(); expect(screen.queryByRole("button", { name: "Criar viagem" })).not.toBeInTheDocument();
    await screen.findByRole("alert");
    expect(screen.queryByRole("button", { name: "Conferir carregamento" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("button", { name: "Criar viagem" })).toBeInTheDocument();
  });
  it("conferente abre sessao mas nao cria operacao nem acessa viagem", async () => {
    vi.mocked(getLoadPlanContinuity).mockResolvedValue({ operational_ready: true, loading_session: { id: "s1", status: "PENDING" }, trip: null });
    setup(false); await screen.findByRole("link", { name: "Abrir carregamento existente" });
    expect(screen.queryByRole("button", { name: "Criar viagem" })).not.toBeInTheDocument();
  });
  it("nao oferece operacao para distribuicao ainda bloqueada", async () => {
    vi.mocked(getLoadPlanContinuity).mockResolvedValue({ operational_ready: false, loading_session: null, trip: null });
    setup(); expect(await screen.findByText(/não está liberado/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Criar viagem" })).not.toBeInTheDocument();
  });
  it("reconsulta apos conflito de viagem criada por outro processo", async () => {
    vi.mocked(getLoadPlanContinuity).mockResolvedValueOnce({ operational_ready: true, loading_session: null, trip: null }).mockResolvedValue({ operational_ready: true, loading_session: null, trip: { id: "v2", status: "SCHEDULED" } });
    setup(); fireEvent.click(await screen.findByRole("button", { name: "Criar viagem" }));
    expect(await screen.findByRole("link", { name: "Abrir viagem existente" })).toHaveAttribute("href", "/trips/v2");
  });
});
