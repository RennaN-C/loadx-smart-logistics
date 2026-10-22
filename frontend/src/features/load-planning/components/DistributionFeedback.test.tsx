import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiError } from "../../../types/api";
import { DistributionFeedback } from "./DistributionFeedback";

describe("DistributionFeedback - resultado incerto da otimizacao", () => {
  it("orienta consultar os planos persistidos quando conexao cai sem resposta", () => {
    render(<DistributionFeedback error={new ApiError("NETWORK_ERROR", "Falha de conexão")} />);
    expect(screen.getByText(/A distribuição pode ter sido salva no servidor/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Conferir Planos existentes/ })).toHaveAttribute("href", "/planning");
    expect(screen.getByText(/antes de repetir a otimização/)).toBeInTheDocument();
  });

  it("nao trata erro HTTP confirmado como resultado incerto", () => {
    render(<DistributionFeedback error={new ApiError("UNKNOWN_ERROR", "Erro do servidor", [], 500)} />);
    expect(screen.queryByText(/A distribuição pode ter sido salva no servidor/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Conferir Planos existentes/ })).not.toBeInTheDocument();
  });

  it("mantem o codigo de conflito de pedido sem criar proposta duplicada", () => {
    render(<DistributionFeedback error={new ApiError("DISTRIBUTION_ORDER_CLAIMED", "Conflito", [], 409)} />);
    expect(screen.getByText(/pedido já pertence a outra distribuição ativa/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Conferir Planos existentes/ })).not.toBeInTheDocument();
  });

  it("nao exibe feedback quando nao existe erro", () => {
    render(<DistributionFeedback error={null} />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
