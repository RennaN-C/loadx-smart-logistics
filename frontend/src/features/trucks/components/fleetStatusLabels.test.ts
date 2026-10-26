import { describe, expect, it } from "vitest";

import type { TruckOperationalStatus } from "../types";
import { describeFleetStatus } from "./fleetStatusLabels";

function truck(overrides: Partial<TruckOperationalStatus> = {}): TruckOperationalStatus {
  return {
    id: "t1",
    plate: "ABC1D23",
    model: "Baú",
    active: true,
    hasOperationConflict: false,
    available: true,
    ...overrides,
  };
}

describe("describeFleetStatus", () => {
  it("disponível não precisa de justificativa", () => {
    expect(describeFleetStatus(truck())).toEqual({
      tone: "good",
      label: "Disponível",
      reason: null,
    });
  });

  it("explica a indisponibilidade por conflito", () => {
    const view = describeFleetStatus(truck({ hasOperationConflict: true, available: false }));

    expect(view.label).toBe("Indisponível");
    expect(view.reason).toBe("Já está em operação");
    expect(view.tone).toBe("warn");
  });

  it("explica a indisponibilidade por cadastro arquivado", () => {
    const view = describeFleetStatus(truck({ active: false, available: false }));

    expect(view.reason).toBe("Cadastro arquivado");
    // tom diferente do conflito: um é decisão de quem administra, o outro passa
    expect(view.tone).toBe("neutral");
  });

  it("mostra os dois motivos quando os dois valem", () => {
    const view = describeFleetStatus(
      truck({ active: false, hasOperationConflict: true, available: false }),
    );

    expect(view.reason).toBe("Cadastro arquivado e já está em operação");
  });

  it("NÃO recalcula a disponibilidade: quem decide é o backend", () => {
    // Combinação que a regra de hoje não produz. Se o backend passar a produzir,
    // a tela precisa obedecer em vez de corrigir — por isso nada de `active &&
    // !conflito` aqui.
    const view = describeFleetStatus(
      truck({ active: true, hasOperationConflict: true, available: true }),
    );

    expect(view.label).toBe("Disponível");
  });

  it("não inventa motivo quando o backend recusa sem apontar nenhum", () => {
    const view = describeFleetStatus(
      truck({ active: true, hasOperationConflict: false, available: false }),
    );

    expect(view.label).toBe("Indisponível");
    expect(view.reason).toBeNull();
  });
});

it("explica indisponibilidade por manutenção sem confundir arquivamento", () => {
  expect(describeFleetStatus({ id: "t1", plate: "ABC1D23", model: "Baú", active: true, hasOperationConflict: false, hasMaintenanceConflict: true, available: false }).reason).toBe("Em manutenção");
});

it("explica bloqueio pela política documental", () => {
  expect(describeFleetStatus({ id: "t1", plate: "ABC1D23", model: "Baú", active: true, hasOperationConflict: false, hasDocumentConflict: true, available: false }).reason).toBe("Política documental pendente");
});
