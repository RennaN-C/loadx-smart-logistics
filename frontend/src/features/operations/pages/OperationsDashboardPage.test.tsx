import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { getOperationalIndicators } from "../api/operationalIndicatorsApi";
import type { OperationalIndicators } from "../types";
import { OperationsDashboardPage } from "./OperationsDashboardPage";

vi.mock("../api/operationalIndicatorsApi");

function indicadores(overrides: Partial<OperationalIndicators> = {}): OperationalIndicators {
  return {
    fleet: {
      period: "CURRENT_SNAPSHOT",
      total: 6,
      active: 5,
      inactive: 1,
      available: 4,
      unavailable: 2,
      withOperationConflict: 1,
    },
    trips: { period: "ALL_TIME", total: 12, scheduled: 3, inRoute: 2, finished: 7 },
    deliveries: { period: "ALL_TIME", total: 40, pending: 10, inDelivery: 5, delivered: 25 },
    occurrences: { period: "ALL_TIME", total: 3 },
    ...overrides,
  };
}

/** O bloco de um grupo, para o número ser procurado dentro do contexto dele. */
function bloco(titulo: string) {
  const elemento = screen.getByRole("heading", { name: titulo }).closest("section");
  if (elemento === null) throw new Error(`bloco ${titulo} não encontrado`);
  return elemento;
}

function kpi(secao: HTMLElement, rotulo: string) {
  const elemento = within(secao).getByText(rotulo).closest(".ops-kpi");
  if (elemento === null) throw new Error(`indicador ${rotulo} não encontrado`);
  return elemento;
}

describe("OperationsDashboardPage", () => {
  beforeEach(() => {
    vi.mocked(getOperationalIndicators).mockReset();
  });

  it("mostra os números que o backend apurou", async () => {
    vi.mocked(getOperationalIndicators).mockResolvedValue(indicadores());

    render(<OperationsDashboardPage />);
    await screen.findByRole("heading", { name: "Frota" });

    expect(kpi(bloco("Frota"), "DISPONÍVEIS")).toHaveTextContent("4");
    expect(kpi(bloco("Frota"), "EM OPERAÇÃO")).toHaveTextContent("1");
    expect(kpi(bloco("Viagens"), "EM ROTA")).toHaveTextContent("2");
    expect(kpi(bloco("Entregas"), "PENDENTES")).toHaveTextContent("10");
    expect(kpi(bloco("Ocorrências"), "REGISTRADAS")).toHaveTextContent("3");
  });

  it("diz o período de cada grupo, que faz parte do significado", async () => {
    // "2 em rota" sem recorte de tempo não quer dizer nada: a frota é um retrato
    // de agora, viagens e entregas são tudo o que já houve.
    vi.mocked(getOperationalIndicators).mockResolvedValue(indicadores());

    render(<OperationsDashboardPage />);
    await screen.findByRole("heading", { name: "Frota" });

    expect(within(bloco("Frota")).getByText("situação agora")).toBeInTheDocument();
    expect(within(bloco("Viagens")).getByText("desde o início")).toBeInTheDocument();
    expect(within(bloco("Entregas")).getByText("desde o início")).toBeInTheDocument();
  });

  it("mostra período desconhecido cru, em vez de traduzir por chute", async () => {
    // Se a OC69 ganhar um período novo, a tela não pode inventar um nome para ele.
    vi.mocked(getOperationalIndicators).mockResolvedValue(
      indicadores({
        trips: {
          period: "LAST_30_DAYS" as never,
          total: 1,
          scheduled: 1,
          inRoute: 0,
          finished: 0,
        },
      }),
    );

    render(<OperationsDashboardPage />);
    await screen.findByRole("heading", { name: "Viagens" });

    expect(within(bloco("Viagens")).getByText("LAST_30_DAYS")).toBeInTheDocument();
  });

  it("não exibe porcentagem nenhuma: a OC69 não publica taxa", async () => {
    // 4 de 6 disponíveis daria "67%", e seria métrica derivada no cliente —
    // justamente o que a OC74 põe fora de escopo.
    vi.mocked(getOperationalIndicators).mockResolvedValue(indicadores());

    render(<OperationsDashboardPage />);
    await screen.findByRole("heading", { name: "Frota" });

    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it("base vazia mostra zeros, não erro: o backend responde 200", async () => {
    vi.mocked(getOperationalIndicators).mockResolvedValue({
      fleet: {
        period: "CURRENT_SNAPSHOT",
        total: 0,
        active: 0,
        inactive: 0,
        available: 0,
        unavailable: 0,
        withOperationConflict: 0,
      },
      trips: { period: "ALL_TIME", total: 0, scheduled: 0, inRoute: 0, finished: 0 },
      deliveries: { period: "ALL_TIME", total: 0, pending: 0, inDelivery: 0, delivered: 0 },
      occurrences: { period: "ALL_TIME", total: 0 },
    });

    render(<OperationsDashboardPage />);
    await screen.findByRole("heading", { name: "Frota" });

    expect(kpi(bloco("Frota"), "CAMINHÕES")).toHaveTextContent("0");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("ocorrência zerada não fica em vermelho", async () => {
    vi.mocked(getOperationalIndicators).mockResolvedValue(
      indicadores({ occurrences: { period: "ALL_TIME", total: 0 } }),
    );

    render(<OperationsDashboardPage />);
    await screen.findByRole("heading", { name: "Ocorrências" });

    expect(kpi(bloco("Ocorrências"), "REGISTRADAS")).not.toHaveClass("ops-kpi-alert");
  });

  it("destaca ocorrência registrada, que é o que pede ação", async () => {
    vi.mocked(getOperationalIndicators).mockResolvedValue(indicadores());

    render(<OperationsDashboardPage />);
    await screen.findByRole("heading", { name: "Ocorrências" });

    expect(kpi(bloco("Ocorrências"), "REGISTRADAS")).toHaveClass("ops-kpi-alert");
  });

  it("mostra o carregando antes dos dados", () => {
    vi.mocked(getOperationalIndicators).mockReturnValue(new Promise(() => undefined));

    render(<OperationsDashboardPage />);

    expect(screen.getByText("Carregando indicadores…")).toBeInTheDocument();
  });

  it("oferece nova tentativa quando a consulta falha", async () => {
    vi.mocked(getOperationalIndicators).mockRejectedValueOnce(
      new ApiError("NETWORK_ERROR", "sem rede"),
    );

    render(<OperationsDashboardPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/conexão/i);

    vi.mocked(getOperationalIndicators).mockResolvedValue(indicadores());
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(await screen.findByRole("heading", { name: "Frota" })).toBeInTheDocument();
  });

  it("404 diz que a API não está publicada, em vez de 'erro inesperado'", async () => {
    // O 404 do FastAPI não usa o envelope do projeto, então chega como
    // UNKNOWN_ERROR: sem olhar o status, a tela mandaria procurar defeito no
    // lugar errado. Foi o que aconteceu no ambiente local antes da OC69 subir.
    vi.mocked(getOperationalIndicators).mockRejectedValue(
      new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.", [], 404),
    );

    render(<OperationsDashboardPage />);

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent(/ainda não publica a API de indicadores/i);
    expect(aviso).not.toHaveTextContent(/inesperado/i);
  });

  it("um 500 continua caindo no erro genérico: a causa não é conhecida", async () => {
    vi.mocked(getOperationalIndicators).mockRejectedValue(
      new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.", [], 500),
    );

    render(<OperationsDashboardPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/inesperado/i);
  });

  it("explica o 403 em vez de mostrar painel vazio", async () => {
    vi.mocked(getOperationalIndicators).mockRejectedValue(
      new ApiError("AUTH_FORBIDDEN", "Acesso negado."),
    );

    render(<OperationsDashboardPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/permissão/i);
  });

  it("o botão Atualizar relê os indicadores", async () => {
    vi.mocked(getOperationalIndicators).mockResolvedValue(indicadores());

    render(<OperationsDashboardPage />);
    await screen.findByRole("heading", { name: "Frota" });

    vi.mocked(getOperationalIndicators).mockResolvedValue(
      indicadores({
        trips: { period: "ALL_TIME", total: 13, scheduled: 3, inRoute: 3, finished: 7 },
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Atualizar" }));

    await waitFor(() => expect(kpi(bloco("Viagens"), "EM ROTA")).toHaveTextContent("3"));
  });
});
