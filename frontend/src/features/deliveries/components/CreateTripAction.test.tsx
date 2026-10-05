import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { listDriverOperationalStatus, listDrivers } from "../../drivers/api/driversApi";
import { createTrip } from "../api/tripsApi";
import { CreateTripAction } from "./CreateTripAction";

vi.mock("../../drivers/api/driversApi");
vi.mock("../api/tripsApi");

function renderAction() {
  return render(
    <MemoryRouter>
      <CreateTripAction loadPlanId="lp1" />
    </MemoryRouter>,
  );
}

describe("CreateTripAction", () => {
  beforeEach(() => {
    vi.resetAllMocks();

    vi.mocked(listDrivers).mockResolvedValue(
      makePage([
        {
          id: "d1",
          name: "Motorista Livre",
          licenseCategory: "D",
          active: true,
          createdAt: "2026-08-01T00:00:00Z",
        },
        {
          id: "d2",
          name: "Motorista Ocupado",
          licenseCategory: "E",
          active: true,
          createdAt: "2026-08-01T00:00:00Z",
        },
      ]),
    );

    vi.mocked(listDriverOperationalStatus).mockResolvedValue(
      makePage([
        {
          id: "d1",
          name: "Motorista Livre",
          licenseCategory: "D",
          active: true,
          hasOperationConflict: false,
          available: true,
        },
        {
          id: "d2",
          name: "Motorista Ocupado",
          licenseCategory: "E",
          active: true,
          hasOperationConflict: true,
          available: false,
        },
      ]),
    );
  });

  it("mantém disponível quem a OC67 informa como livre", async () => {
    renderAction();
    fireEvent.click(screen.getByRole("button", { name: "Criar viagem" }));

    const select = await screen.findByLabelText("MOTORISTA");
    await waitFor(() => expect(select.querySelectorAll("option")).toHaveLength(3));

    const livre = [...select.querySelectorAll("option")].find((option) => option.value === "d1");
    expect(livre).toBeDefined();
    expect(livre).not.toBeDisabled();
    expect(livre?.textContent).not.toContain("em operação");
  });

  it("bloqueia visualmente motorista em outra operação", async () => {
    renderAction();
    fireEvent.click(screen.getByRole("button", { name: "Criar viagem" }));

    const select = await screen.findByLabelText("MOTORISTA");
    await waitFor(() =>
      expect([...select.querySelectorAll("option")].some((option) => option.value === "d2")).toBe(true),
    );

    const ocupado = [...select.querySelectorAll("option")].find((option) => option.value === "d2");
    expect(ocupado).toBeDisabled();
    expect(ocupado?.textContent).toContain("em operação");
  });

  it("explica falha na consulta sem fingir que conhece a disponibilidade", async () => {
    vi.mocked(listDriverOperationalStatus).mockRejectedValue(
      new ApiError("NETWORK_ERROR", "Falha de rede."),
    );

    renderAction();
    fireEvent.click(screen.getByRole("button", { name: "Criar viagem" }));

    expect(
      await screen.findByText(/Não foi possível confirmar a disponibilidade agora/),
    ).toBeInTheDocument();

    const select = screen.getByLabelText("MOTORISTA");
    await waitFor(() => expect(select.querySelectorAll("option")).toHaveLength(3));

    const livre = [...select.querySelectorAll("option")].find((option) => option.value === "d1");
    expect(livre).not.toBeDisabled();
  });

  it("não chama criação com opção indisponível", async () => {
    renderAction();
    fireEvent.click(screen.getByRole("button", { name: "Criar viagem" }));

    const select = await screen.findByLabelText("MOTORISTA");
    await waitFor(() =>
      expect([...select.querySelectorAll("option")].some((option) => option.value === "d2")).toBe(true),
    );

    fireEvent.change(select, { target: { value: "d2" } });

    expect(screen.getByRole("button", { name: "Criar viagem" })).toBeDisabled();
    expect(createTrip).not.toHaveBeenCalled();
  });
});
