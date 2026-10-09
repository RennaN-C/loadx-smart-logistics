import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { listTripAttachmentOccurrences } from "../api/attachmentsApi";
import { TripAttachments } from "./TripAttachments";
import type { Trip } from "../../deliveries/types";
vi.mock("../api/attachmentsApi", () => ({ listTripAttachmentOccurrences: vi.fn() }));
vi.mock("./AttachmentPanel", () => ({ AttachmentPanel: ({ resource, resourceId }: { resource: string; resourceId: string }) => <p>{resource}:{resourceId}</p> }));
const trip: Trip = { id: "t1", loadPlanId: "p1", driverId: "m1", status: "SCHEDULED", startedAt: null, finishedAt: null, deliveries: [{ id: "d1", tripId: "t1", orderId: "o1", status: "PENDING", sequence: 1, deliveredAt: null }] };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(listTripAttachmentOccurrences).mockResolvedValue([{ id: "oc1", type: "OTHER", description: "Fixture" }]); });
it("abre sob demanda e seleciona viagem, entrega e ocorrência", async () => {
  render(<TripAttachments trip={trip} canManage />);
  expect(listTripAttachmentOccurrences).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Anexos da viagem e entregas" }));
  expect(screen.getByText("trips:t1")).toBeInTheDocument();
  await screen.findByRole("option", { name: "Ocorrência OTHER: Fixture" });
  fireEvent.change(screen.getByLabelText("Recurso do anexo"), { target: { value: "deliveries:d1" } });
  expect(screen.getByText("deliveries:d1")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Recurso do anexo"), { target: { value: "occurrences:oc1" } });
  expect(screen.getByText("occurrences:oc1")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
it("falha de ocorrências preserva contexto viagem e entrega", async () => {
  vi.mocked(listTripAttachmentOccurrences).mockRejectedValue(new Error("Falha"));
  render(<TripAttachments trip={trip} canManage />);
  fireEvent.click(screen.getByRole("button", { name: "Anexos da viagem e entregas" }));
  await waitFor(() => expect(screen.getByText(/Não foi possível consultar ocorrências/)).toBeInTheDocument());
  expect(screen.getByRole("option", { name: "Entrega 1" })).toBeInTheDocument();
});
