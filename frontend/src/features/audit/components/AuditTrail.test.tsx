import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { listAuditEntries } from "../api/auditApi";
import { AuditTrail } from "./AuditTrail";

vi.mock("../api/auditApi");

describe("AuditTrail", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("oferece nova tentativa quando o histórico falha, sem bloquear o contexto", async () => {
    vi.mocked(listAuditEntries).mockRejectedValueOnce(new Error("indisponível")).mockResolvedValueOnce(makePage([]));

    render(<AuditTrail entityType="ORDER" entityId="o1" title="Histórico do pedido" />);

    expect(await screen.findByText("Histórico indisponível no momento.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar carregar histórico novamente" }));
    expect(await screen.findByText("Nenhum evento registrado para este item.")).toBeInTheDocument();
    expect(listAuditEntries).toHaveBeenCalledTimes(2);
  });

  it("consulta somente a entidade contextual e mostra o ator", async () => {
    vi.mocked(listAuditEntries).mockResolvedValue(
      makePage([
        {
          id: "h1",
          eventType: "STATUS_CHANGED",
          entityType: "TRIP",
          entityId: "t1",
          actorId: "u1",
          actorName: "Rennan",
          oldStatus: "SCHEDULED",
          newStatus: "IN_ROUTE",
          changedFields: [],
          createdAt: "2026-10-06T18:00:00Z",
        },
      ]),
    );

    render(<AuditTrail entityType="TRIP" entityId="t1" title="Histórico da viagem" />);

    expect(await screen.findByText("Rennan")).toBeInTheDocument();
    expect(screen.getByText("Agendada → Em rota")).toBeInTheDocument();
    expect(listAuditEntries).toHaveBeenCalledWith({
      entityType: "TRIP",
      entityId: "t1",
      page: 1,
      pageSize: 8,
      sortOrder: "desc",
    });
  });
  it("oculta eventos anteriores enquanto consulta outra entidade", async () => {
    vi.mocked(listAuditEntries).mockResolvedValueOnce(makePage([{
      id: "h1", eventType: "STATUS_CHANGED", entityType: "ORDER", entityId: "o1",
      actorId: "u1", actorName: "Ator anterior", oldStatus: "DRAFT", newStatus: "READY",
      changedFields: [], createdAt: "2026-10-06T18:00:00Z",
    }])).mockImplementationOnce(() => new Promise(() => {}));
    const { rerender } = render(<AuditTrail entityType="ORDER" entityId="o1" />);
    expect(await screen.findByText("Ator anterior")).toBeInTheDocument();
    rerender(<AuditTrail entityType="ORDER" entityId="o2" />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando histórico");
    expect(screen.queryByText("Ator anterior")).not.toBeInTheDocument();
  });

});
