import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { listTruckOperationalStatus } from "../api/trucksApi";
import type { TruckOperationalStatus } from "../types";
import { FleetStatusPage } from "./FleetStatusPage";

vi.mock("../api/trucksApi");

function truck(overrides: Partial<TruckOperationalStatus> = {}): TruckOperationalStatus {
  return {
    id: "t1",
    plate: "ABC1D23",
    model: "Baú 6m",
    active: true,
    hasOperationConflict: false,
    available: true,
    ...overrides,
  };
}

const DISPONIVEL = truck();
const EM_OPERACAO = truck({
  id: "t2",
  plate: "DEF2E34",
  hasOperationConflict: true,
  available: false,
});
const INATIVO = truck({ id: "t3", plate: "GHI3F45", active: false, available: false });

function cartao(placa: string) {
  const elemento = screen.getByText(placa).closest("li");
  if (elemento === null) throw new Error(`cartão de ${placa} não encontrado`);
  return elemento;
}

describe("FleetStatusPage", () => {
  beforeEach(() => {
    vi.mocked(listTruckOperationalStatus).mockReset();
  });

  it("mostra a situação que o backend calculou", async () => {
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(
      makePage([DISPONIVEL, EM_OPERACAO, INATIVO]),
    );

    render(<FleetStatusPage />);

    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
    expect(within(cartao("ABC1D23")).getByText("Disponível")).toBeInTheDocument();
    expect(within(cartao("DEF2E34")).getByText("Indisponível")).toBeInTheDocument();
    expect(within(cartao("GHI3F45")).getByText("Indisponível")).toBeInTheDocument();
  });

  it("diz POR QUE o caminhão não está disponível", async () => {
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([EM_OPERACAO, INATIVO]));

    render(<FleetStatusPage />);
    await screen.findByText("DEF2E34");

    expect(within(cartao("DEF2E34")).getByText("Já está em operação")).toBeInTheDocument();
    expect(within(cartao("GHI3F45")).getByText("Cadastro arquivado")).toBeInTheDocument();
  });

  it("não ocupa linha com motivo quando o caminhão está disponível", async () => {
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([DISPONIVEL]));

    render(<FleetStatusPage />);
    await screen.findByText("ABC1D23");

    expect(within(cartao("ABC1D23")).queryByText(/operação|arquivado/i)).not.toBeInTheDocument();
  });

  it("deixa claro que a contagem vale para a página, não para a frota", async () => {
    // Sem esta frase, "2 de 3 disponíveis" passaria por total da frota, e D12
    // mantém agregação server-side fora do contrato.
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(
      makePage([DISPONIVEL, EM_OPERACAO, INATIVO]),
    );

    render(<FleetStatusPage />);

    expect(await screen.findByText(/1 de 3 disponíveis nesta página/)).toBeInTheDocument();
    expect(screen.getByText(/O filtro\s+atua nesta página/)).toBeInTheDocument();
  });

  it("filtra por disponibilidade", async () => {
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(
      makePage([DISPONIVEL, EM_OPERACAO, INATIVO]),
    );

    render(<FleetStatusPage />);
    await screen.findByText("ABC1D23");

    fireEvent.change(screen.getByLabelText("Filtrar por disponibilidade"), {
      target: { value: "available" },
    });
    expect(screen.getByText("ABC1D23")).toBeInTheDocument();
    expect(screen.queryByText("DEF2E34")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Filtrar por disponibilidade"), {
      target: { value: "unavailable" },
    });
    expect(screen.queryByText("ABC1D23")).not.toBeInTheDocument();
    expect(screen.getByText("DEF2E34")).toBeInTheDocument();
    expect(screen.getByText("GHI3F45")).toBeInTheDocument();
  });

  it("explica o vazio do filtro sem sugerir que a frota está vazia", async () => {
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([DISPONIVEL]));

    render(<FleetStatusPage />);
    await screen.findByText("ABC1D23");

    fireEvent.change(screen.getByLabelText("Filtrar por disponibilidade"), {
      target: { value: "unavailable" },
    });

    expect(screen.getByText("Nenhum caminhão nesta situação, nesta página.")).toBeInTheDocument();
  });

  it("mostra o carregando antes dos dados", () => {
    vi.mocked(listTruckOperationalStatus).mockReturnValue(new Promise(() => undefined));

    render(<FleetStatusPage />);

    expect(screen.getByText("Carregando a situação da frota…")).toBeInTheDocument();
  });

  it("explica a frota vazia", async () => {
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([]));

    render(<FleetStatusPage />);

    expect(await screen.findByText("Nenhum caminhão cadastrado ainda.")).toBeInTheDocument();
  });

  it("oferece nova tentativa quando a consulta falha", async () => {
    vi.mocked(listTruckOperationalStatus).mockRejectedValueOnce(
      new ApiError("NETWORK_ERROR", "sem rede"),
    );

    render(<FleetStatusPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/conexão/i);

    vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([DISPONIVEL]));
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
  });

  it("o botão Atualizar relê a situação, que muda sozinha durante o dia", async () => {
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([DISPONIVEL]));

    render(<FleetStatusPage />);
    await screen.findByText("ABC1D23");

    vi.mocked(listTruckOperationalStatus).mockResolvedValue(
      makePage([truck({ hasOperationConflict: true, available: false })]),
    );
    fireEvent.click(screen.getByRole("button", { name: "Atualizar" }));

    await waitFor(() =>
      expect(within(cartao("ABC1D23")).getByText("Indisponível")).toBeInTheDocument(),
    );
  });

  it("obedece ao backend em vez de refazer a conta da disponibilidade", async () => {
    // Combinação que a regra de hoje não produz: conflito E disponível. Se o
    // backend mudar a regra, a tela precisa acompanhar sem ser corrigida.
    vi.mocked(listTruckOperationalStatus).mockResolvedValue(
      makePage([truck({ hasOperationConflict: true, available: true })]),
    );

    render(<FleetStatusPage />);
    await screen.findByText("ABC1D23");

    expect(within(cartao("ABC1D23")).getByText("Disponível")).toBeInTheDocument();
  });
});
