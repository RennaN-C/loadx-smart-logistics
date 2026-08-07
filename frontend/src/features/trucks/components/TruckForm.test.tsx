import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { createTruck, updateTruck } from "../api/trucksApi";
import type { Truck } from "../types";
import { TruckForm } from "./TruckForm";
import { mapTruckErrorToMessage } from "./trucksErrorMessages";

vi.mock("../api/trucksApi");

const TRUCK: Truck = {
  id: "22222222-2222-2222-2222-222222222222",
  plate: "ABC1D23",
  model: "Baú médio",
  internalWidthCm: 240,
  internalHeightCm: 260,
  internalLengthCm: 600,
  maxWeightKg: 8000,
  active: true,
  createdAt: "2026-08-01T12:00:00Z",
};

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("PLACA"), { target: { value: "xyz9k88" } });
  fireEvent.change(screen.getByLabelText("MODELO"), { target: { value: "Baú novo" } });
  fireEvent.change(screen.getByLabelText("LARGURA (CM)"), { target: { value: "250" } });
  fireEvent.change(screen.getByLabelText("ALTURA (CM)"), { target: { value: "270" } });
  fireEvent.change(screen.getByLabelText("COMPRIMENTO (CM)"), { target: { value: "700" } });
  fireEvent.change(screen.getByLabelText("PESO MÁXIMO (KG)"), { target: { value: "9000" } });
}

describe("mapTruckErrorToMessage", () => {
  it("traduz TRUCK_PLATE_ALREADY_EXISTS", () => {
    expect(mapTruckErrorToMessage(new ApiError("TRUCK_PLATE_ALREADY_EXISTS", "conflito"))).toBe(
      "Já existe um caminhão cadastrado com esta placa.",
    );
  });

  it("usa a mensagem do backend para qualquer outro código", () => {
    expect(mapTruckErrorToMessage(new ApiError("VALIDATION_ERROR", "Dados inválidos."))).toBe("Dados inválidos.");
  });
});

describe("TruckForm", () => {
  beforeEach(() => {
    vi.mocked(createTruck).mockReset();
    vi.mocked(updateTruck).mockReset();
  });

  it("normaliza a placa em maiúsculas e cria o caminhão", async () => {
    vi.mocked(createTruck).mockResolvedValue(TRUCK);
    const onSaved = vi.fn();

    render(<TruckForm onSaved={onSaved} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar caminhão" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(createTruck).toHaveBeenCalledWith({
      plate: "XYZ9K88",
      model: "Baú novo",
      internalWidthCm: 250,
      internalHeightCm: 270,
      internalLengthCm: 700,
      maxWeightKg: 9000,
    });
  });

  it("calcula o volume interno conforme as medidas digitadas", () => {
    render(<TruckForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();

    // 2,50 m x 2,70 m x 7,00 m = 47,25 m³
    expect(screen.getByText("47,25 m³")).toBeInTheDocument();
  });

  it("mostra a mensagem mapeada quando a placa já existe", async () => {
    vi.mocked(createTruck).mockRejectedValue(new ApiError("TRUCK_PLATE_ALREADY_EXISTS", "conflito"));

    render(<TruckForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar caminhão" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Já existe um caminhão cadastrado com esta placa.",
    );
  });

  it("só expõe o campo 'ativo' na edição", () => {
    const { unmount } = render(<TruckForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.queryByLabelText("Caminhão ativo")).not.toBeInTheDocument();
    unmount();

    render(<TruckForm truck={TRUCK} onSaved={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText("Caminhão ativo")).toBeInTheDocument();
  });

  it("envia active junto na edição", async () => {
    vi.mocked(updateTruck).mockResolvedValue({ ...TRUCK, active: false });
    const onSaved = vi.fn();

    render(<TruckForm truck={TRUCK} onSaved={onSaved} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByLabelText("Caminhão ativo"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(updateTruck).toHaveBeenCalledWith(TRUCK.id, expect.objectContaining({ active: false }));
  });
});
