import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { listAuditEntries } from "../api/auditApi";
import type { AuditEntry } from "../types";
import { AuditPage } from "./AuditPage";

vi.mock("../api/auditApi");

const ENTRY: AuditEntry = {
  id: "a1",
  eventType: "STATUS_CHANGED",
  entityType: "ORDER",
  entityId: "11111111-1111-1111-1111-111111111111",
  actorId: "22222222-2222-2222-2222-222222222222",
  actorName: "Ana Souza",
  oldStatus: "DRAFT",
  newStatus: "READY",
  changedFields: [],
  createdAt: "2026-10-06T18:00:00Z",
};

describe("AuditPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listAuditEntries).mockResolvedValue(makePage([ENTRY]));
  });

  it("mostra quem alterou, quando e o que mudou", async () => {
    render(<AuditPage />);

    expect(await screen.findByText("Ana Souza")).toBeInTheDocument();
    expect(screen.getByText("DRAFT → READY")).toBeInTheDocument();
    expect(screen.getByText("Pedido")).toBeInTheDocument();
    expect(screen.getByText(/06\/10\/2026/)).toBeInTheDocument();
  });

  it("aplica filtros por entidade e evento no servidor", async () => {
    render(<AuditPage />);
    await screen.findByText("Ana Souza");

    fireEvent.change(screen.getByLabelText("Entidade"), {
      target: { value: "ORDER" },
    });
    fireEvent.change(screen.getByLabelText("Evento"), {
      target: { value: "STATUS_CHANGED" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() =>
      expect(listAuditEntries).toHaveBeenLastCalledWith(
        expect.objectContaining({
          entityType: "ORDER",
          eventType: "STATUS_CHANGED",
          page: 1,
          pageSize: 20,
        }),
      ),
    );
  });

  it("informa que os filtros acontecem antes da paginação", async () => {
    render(<AuditPage />);

    await screen.findByText("Ana Souza");
    expect(screen.getByText(/aplicados pelo servidor antes da paginação/i)).toBeInTheDocument();
  });
});
