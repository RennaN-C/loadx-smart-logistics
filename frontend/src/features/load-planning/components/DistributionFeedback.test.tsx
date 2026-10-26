import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiError } from "../../../types/api";
import { DistributionFeedback } from "./DistributionFeedback";

describe("DistributionFeedback - resultado incerto da otimizacao", () => {
  it("orienta consultar os planos persistidos quando conexao cai sem resposta", () => {
    render(<DistributionFeedback error={new ApiError("NETWORK_ERROR", "Falha de conexão")} />);
    expect(screen.getByText(/A distribuição pode ter sido salva no servidor/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Conferir Planos existentes/ })).toHaveAttribute("href", "/planning");
    expect(screen.getByText(/antes de repetir a operação/)).toBeInTheDocument();
  });

  it("não trata rejeição de domínio confirmada como resultado incerto", () => {
    render(<DistributionFeedback error={new ApiError("DISTRIBUTION_CAPACITY_INSUFFICIENT", "Sem capacidade", [], 422)} />);
    expect(screen.queryByText(/A distribuição pode ter sido salva no servidor/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Conferir Planos existentes/ })).not.toBeInTheDocument();
  });

  it.each([408, 500, 502, 503, 504])("HTTP %i não prova rollback nem permite outra identidade", (status) => {
    render(<DistributionFeedback error={new ApiError("UNKNOWN_ERROR", "Resposta sem confirmação", [], status)} />);
    expect(screen.getByText(/A distribuição pode ter sido salva no servidor/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Conferir Planos existentes/ })).toBeInTheDocument();
  });

  it("mantem o codigo de conflito de pedido sem criar proposta duplicada", () => {
    render(<DistributionFeedback error={new ApiError("DISTRIBUTION_ORDER_CLAIMED", "Conflito", [], 409)} />);
    expect(screen.getByText(/pedido já pertence a outra distribuição ativa/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Conferir Planos existentes/ })).not.toBeInTheDocument();
  });

  it("traduz falha de capacidade em diagnóstico legível, sem códigos ou JSON bruto", () => {
    const technicalId = "2991699d-f885-4f12-9ccd-1d2933391bc1";
    const details = [{
      remaining_volumes: [
        { order_item_id: technicalId, volume_index: 49, reasons: ["COLLISION"] },
        { order_item_id: technicalId, volume_index: 50, reasons: ["COLLISION"] },
      ],
      ineligible_trucks: [{ truck_id: "internal-truck-id", reason: "TRUCK_OPERATION_CONFLICT" }],
      attempt_count: 10,
    }];
    render(<DistributionFeedback error={new ApiError("DISTRIBUTION_CAPACITY_INSUFFICIENT", "A distribuição não permite esta operação.", details, 422)} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("2 volumes ficaram sem posição segura");
    expect(alert).toHaveTextContent("Não foi encontrada posição livre sem sobrepor volumes.");
    expect(alert).toHaveTextContent("1 caminhão não estava elegível");
    expect(alert).toHaveTextContent("Como resolver:");
    expect(alert).not.toHaveTextContent("DISTRIBUTION_CAPACITY_INSUFFICIENT");
    expect(alert).not.toHaveTextContent("COLLISION");
    expect(alert).not.toHaveTextContent(technicalId);
    expect(alert).not.toHaveTextContent("volume_index");
    expect(alert).not.toHaveTextContent("A distribuição não permite esta operação");
    expect(screen.queryByText("Detalhes da resposta")).not.toBeInTheDocument();
    expect(alert.querySelector("pre")).toBeNull();
  });

  it("ignora detalhes de resposta malformados sem expor conteúdo técnico", () => {
    render(<DistributionFeedback error={new ApiError("DISTRIBUTION_CAPACITY_INSUFFICIENT", "raw system detail", [{ remaining_volumes: "invalid" }, { stack_trace: "secret" }], 422)} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Como resolver:");
    expect(alert).not.toHaveTextContent("raw system detail");
    expect(alert).not.toHaveTextContent("stack_trace");
  });

  it("não exibe mensagem bruta do servidor para outros erros de domínio", () => {
    render(<DistributionFeedback error={new ApiError("TRUCK_OPERATION_CONFLICT", "TRUCK_OPERATION_CONFLICT debugging", [{ truck_id: "interno" }], 409)} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("O caminhão está comprometido com outra operação.");
    expect(alert).not.toHaveTextContent("TRUCK_OPERATION_CONFLICT");
    expect(alert).not.toHaveTextContent("interno");
  });

  it("nao exibe feedback quando nao existe erro", () => {
    render(<DistributionFeedback error={null} />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
