import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { makePage } from "../../../tests/makePage";
import { listAuditEntries } from "../../audit/api/auditApi";
import type { AuditEntry } from "../../audit/types";
import { PlanningActivity } from "./PlanningActivity";

vi.mock("../../audit/api/auditApi");
beforeEach(() => vi.resetAllMocks());
const event: AuditEntry = { id: "event", entityId: "plan-1234", entityType: "LOAD_PLAN", eventType: "STATUS_CHANGED", actorId: null, actorName: "Gestor fictício", oldStatus: null, newStatus: "CALCULATED", changedFields: [], createdAt: "2026-10-25T12:00:00Z" };
it("combina os eventos reais dos três tipos em ordem temporal e mostra transições", async () => {
  vi.mocked(listAuditEntries).mockImplementation(async ({ entityType } = {}) => makePage(entityType === "LOAD_PLAN" ? [event] : entityType === "LOAD_DISTRIBUTION" ? [{ ...event, id: "newer", entityType, entityName: "Distribuição de teste", createdAt: "2026-10-25T13:00:00Z", newStatus: "APPROVED" }] : []));
  render(<MemoryRouter><PlanningActivity /></MemoryRouter>);
  await screen.findByText(/Distribuição de teste/);
  const rows = screen.getAllByRole("listitem");
  expect(within(rows[0]).getByText("Aprovado")).toBeInTheDocument();
  expect(within(rows[1]).getByText("Calculado")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Ver todas →" })).toHaveAttribute("href", "/audit");
});
it("mostra erro e permite nova consulta sem apresentar histórico fictício", async () => {
  vi.mocked(listAuditEntries).mockRejectedValue(new Error("offline"));
  render(<MemoryRouter><PlanningActivity /></MemoryRouter>);
  await screen.findByRole("alert");
  expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  vi.mocked(listAuditEntries).mockResolvedValue(makePage([]));
  fireEvent.click(screen.getByRole("button", { name: "Recarregar atividade" }));
  expect(await screen.findByText("Nenhuma atividade de planejamento registrada.")).toBeInTheDocument();
});
