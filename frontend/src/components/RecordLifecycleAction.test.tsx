import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../services/api";
import { ApiError } from "../types/api";
import { RecordLifecycleAction } from "./RecordLifecycleAction";

vi.mock("../services/api", () => ({ api: { patch: vi.fn() } }));

beforeEach(() => vi.clearAllMocks());

describe("RecordLifecycleAction", () => {
  it.each(["customers", "products", "trucks", "drivers"] as const)("arquiva %s pelo contrato existente e atualiza a lista", async (resource) => {
    vi.mocked(api.patch).mockResolvedValue({ data: { active: false } });
    const onChanged = vi.fn().mockResolvedValue(undefined);
    render(<RecordLifecycleAction resource={resource} id="record-id" active onChanged={onChanged} />);
    fireEvent.click(screen.getByRole("button", { name: "Arquivar" }));
    expect(screen.getByRole("button", { name: "Salvando…" })).toBeDisabled();
    await waitFor(() => expect(onChanged).toHaveBeenCalledOnce());
    expect(api.patch).toHaveBeenCalledExactlyOnceWith(`/${resource}/record-id`, { active: false });
  });

  it("reativa sem recriar a identidade", async () => {
    vi.mocked(api.patch).mockResolvedValue({ data: { active: true } });
    const onChanged = vi.fn().mockResolvedValue(undefined);
    render(<RecordLifecycleAction resource="customers" id="original-id" active={false} onChanged={onChanged} />);
    fireEvent.click(screen.getByRole("button", { name: "Reativar" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledOnce());
    expect(api.patch).toHaveBeenCalledWith("/customers/original-id", { active: true });
  });

  it("preserva a lista e exibe conflito sem anunciar sucesso", async () => {
    vi.mocked(api.patch).mockRejectedValue(new ApiError("CUSTOMER_DOCUMENT_ALREADY_EXISTS", "Documento já cadastrado."));
    const onChanged = vi.fn();
    render(<RecordLifecycleAction resource="customers" id="original-id" active={false} onChanged={onChanged} />);
    fireEvent.click(screen.getByRole("button", { name: "Reativar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Documento já cadastrado.");
    expect(screen.getByRole("button", { name: "Reativar" })).toBeEnabled();
    expect(onChanged).not.toHaveBeenCalled();
  });
});
