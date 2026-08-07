import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { createDriver, updateDriver } from "../api/driversApi";
import type { Driver } from "../types";
import { DriverForm } from "./DriverForm";
import { mapDriverErrorToMessage } from "./driversErrorMessages";

vi.mock("../api/driversApi");

const DRIVER: Driver = {
  id: "d1",
  name: "Carlos Pereira",
  document: "123.456.789-00",
  phone: "(11) 91111-1111",
  licenseNumber: "01234567890",
  licenseCategory: "E",
  active: true,
  createdAt: "2026-08-01T12:00:00Z",
};

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("NOME"), { target: { value: "Rita Alves" } });
  fireEvent.change(screen.getByLabelText("DOCUMENTO"), { target: { value: "987.654.321-00" } });
  fireEvent.change(screen.getByLabelText("TELEFONE"), { target: { value: "(11) 92222-2222" } });
  fireEvent.change(screen.getByLabelText("NÚMERO DA CNH"), { target: { value: "09876543210" } });
}

describe("mapDriverErrorToMessage", () => {
  it("distingue documento duplicado de CNH duplicada", () => {
    expect(mapDriverErrorToMessage(new ApiError("DRIVER_DOCUMENT_ALREADY_EXISTS", "x"))).toBe(
      "Já existe um motorista cadastrado com este documento.",
    );
    expect(mapDriverErrorToMessage(new ApiError("DRIVER_LICENSE_NUMBER_ALREADY_EXISTS", "x"))).toBe(
      "Já existe um motorista cadastrado com este número de CNH.",
    );
  });
});

describe("DriverForm", () => {
  beforeEach(() => {
    vi.mocked(createDriver).mockReset();
    vi.mocked(updateDriver).mockReset();
  });

  it("envia categoria nula quando não é informada", async () => {
    vi.mocked(createDriver).mockResolvedValue(DRIVER);
    const onSaved = vi.fn();

    render(<DriverForm onSaved={onSaved} onCancel={vi.fn()} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar motorista" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(createDriver).toHaveBeenCalledWith({
      name: "Rita Alves",
      document: "987.654.321-00",
      phone: "(11) 92222-2222",
      licenseNumber: "09876543210",
      licenseCategory: null,
    });
  });

  it("oferece só as categorias que dirigem caminhão", () => {
    render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);

    const options = [...screen.getByLabelText("CATEGORIA (OPCIONAL)").querySelectorAll("option")].map(
      (option) => option.value,
    );

    expect(options).toEqual(["", "C", "D", "E", "AC", "AD", "AE"]);
  });

  it("só expõe o campo 'ativo' na edição", () => {
    const { unmount } = render(<DriverForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.queryByLabelText(/Motorista ativo/)).not.toBeInTheDocument();
    unmount();

    render(<DriverForm driver={DRIVER} onSaved={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText(/Motorista ativo/)).toBeInTheDocument();
  });

  it("envia active junto na edição", async () => {
    vi.mocked(updateDriver).mockResolvedValue({ ...DRIVER, active: false });
    const onSaved = vi.fn();

    render(<DriverForm driver={DRIVER} onSaved={onSaved} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByLabelText(/Motorista ativo/));
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(updateDriver).toHaveBeenCalledWith(DRIVER.id, expect.objectContaining({ active: false }));
  });
});
