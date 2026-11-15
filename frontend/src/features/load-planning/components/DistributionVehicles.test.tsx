import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { makeDistribution } from "../testing/distributionFixtures";
import { DistributionVehicles } from "./DistributionVehicles";

describe("distribution vehicle inspection controls", () => {
  it("identifies the selected truck and passes only its existing part ID", () => {
    const parts = makeDistribution().parts;
    const onSelect = vi.fn();
    const { rerender } = render(<DistributionVehicles parts={parts} selectedId={parts[0].id} onSelect={onSelect} />);
    const group = screen.getByRole("group", { name: "Caminhões da distribuição" });
    const first = within(group).getByRole("button", { name: /Caminhão 1/ });
    const second = within(group).getByRole("button", { name: /Caminhão 2/ });
    expect(first).toHaveAttribute("aria-pressed", "true");
    expect(second).toHaveAttribute("aria-pressed", "false");
    expect(second).toHaveTextContent("TST2A23");
    expect(second).toHaveTextContent("20%");
    fireEvent.click(second);
    expect(onSelect).toHaveBeenCalledExactlyOnceWith(parts[1].id);
    rerender(<DistributionVehicles parts={parts} selectedId={parts[1].id} onSelect={onSelect} />);
    expect(first).toHaveAttribute("aria-pressed", "false");
    expect(second).toHaveAttribute("aria-pressed", "true");
  });

  it("uses an accessible selector for a fleet without losing any truck", () => {
    const parts = makeDistribution(10).parts;
    const onSelect = vi.fn();
    render(<DistributionVehicles parts={parts} selectedId={parts[0].id} onSelect={onSelect} />);
    const select = screen.getByRole("combobox", { name: "Caminhão para visualizar" });
    expect(within(select).getAllByRole("option")).toHaveLength(10);
    expect(screen.queryByRole("button", { name: /Caminhão 1/ })).not.toBeInTheDocument();
    fireEvent.change(select, { target: { value: parts[9].id } });
    expect(onSelect).toHaveBeenCalledExactlyOnceWith(parts[9].id);
  });
});
