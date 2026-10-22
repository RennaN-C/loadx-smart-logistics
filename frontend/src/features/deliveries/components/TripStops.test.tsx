import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TripStops } from "./TripStops";
import type { Trip } from "../types";
vi.mock("./DeliveryEvidencePanel", () => ({ DeliveryEvidencePanel: ({ deliveryId }: { deliveryId: string }) => <p>Evidências de {deliveryId}</p> }));
vi.mock("./DeliveryCommunicationPanel", () => ({ DeliveryCommunicationPanel: ({ deliveryId }: { deliveryId: string }) => <p>Comunicação de {deliveryId}</p> }));
const TRIP: Trip = { id: "t1", loadPlanId: "p1", driverId: "m1", status: "IN_ROUTE", startedAt: "2026-10-21T10:00:00Z", finishedAt: null, deliveries: [{ id: "d1", tripId: "t1", orderId: "o1", status: "DELIVERED", sequence: 1, deliveredAt: "2026-10-21T11:00:00Z" }, { id: "d2", tripId: "t1", orderId: "o2", status: "IN_DELIVERY", sequence: 2, deliveredAt: null }] };
describe("Acesso contextual OC81", () => {
  it("não apresenta ações de consulta sem as permissões correspondentes", () => {
    render(<TripStops trip={TRIP} canOperate={false} canReadReceipts={false} canReadCommunication={false} isWorking={false} onAdvance={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /Comprovante/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Comunicação/ })).not.toBeInTheDocument();
  });
  it("abre o comprovante da entrega concluída correta e volta à parada pelo teclado", async () => {
    render(<TripStops trip={TRIP} canOperate={false} canReadReceipts isWorking={false} onAdvance={vi.fn()} />);
    const origin = screen.getByRole("button", { name: "Comprovante da parada 1" }); origin.focus(); fireEvent.click(origin);
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Comprovante — parada 1");
    expect(screen.getByText("Evidências de d1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Comprovante da parada 2" })).not.toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(origin).toHaveFocus();
  });
  it("consulta comunicação também antes da conclusão sem abrir comprovante inexistente", () => {
    render(<TripStops trip={TRIP} canOperate={false} canReadCommunication isWorking={false} onAdvance={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Comunicação da parada 2" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Comunicação — parada 2");
    expect(screen.getByText("Comunicação de d2")).toBeInTheDocument();
  });
});
