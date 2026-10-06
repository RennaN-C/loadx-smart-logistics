import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { listAuditEntries } from "../api/auditApi";
import { AuditTrail } from "./AuditTrail";

vi.mock("../api/auditApi");

describe("AuditTrail", () => {
  beforeEach(() => {
    vi.resetAllMocks();
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
    expect(screen.getByText("SCHEDULED → IN_ROUTE")).toBeInTheDocument();
    expect(listAuditEntries).toHaveBeenCalledWith({
      entityType: "TRIP",
      entityId: "t1",
      page: 1,
      pageSize: 8,
      sortOrder: "desc",
    });
  });
});
