import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { getTrip } from "../api/tripsApi";
import { useTripPage } from "./useTripPage";
import { getLoadingSession } from "../../loading-operation/api/loadingApi";
import { getLoadPlan } from "../../load-planning/api/loadPlansApi";
import { useLoadingSession } from "../../loading-operation/hooks/useLoadingSession";
import { ApiError } from "../../../types/api";
import type { Trip } from "../types";

vi.mock("../api/tripsApi");
vi.mock("../../loading-operation/api/loadingApi");
vi.mock("../../load-planning/api/loadPlansApi");
const trip = (id: string): Trip => ({ id, loadPlanId: "p1", driverId: "d1", status: "SCHEDULED", startedAt: null, finishedAt: null, deliveries: [] });
beforeEach(() => vi.resetAllMocks());

it("trocar viagem e receber 404 não deixa ações ou dados do registro anterior", async () => {
  vi.mocked(getTrip).mockResolvedValueOnce(trip("t1")).mockRejectedValueOnce(new ApiError("TRIP_NOT_FOUND", "Não encontrada", [], 404));
  const view = renderHook(({ id }) => useTripPage(id), { initialProps: { id: "t1" } });
  await waitFor(() => expect(view.result.current.trip?.id).toBe("t1"));
  view.rerender({ id: "t2" });
  expect(view.result.current.trip).toBeNull();
  await waitFor(() => expect(view.result.current.isLoading).toBe(false));
  expect(view.result.current.trip).toBeNull();
  expect(view.result.current.errorMessage).not.toBeNull();
});

it("resposta de ação da viagem antiga não sobrescreve viagem recém-aberta", async () => {
  vi.mocked(getTrip).mockImplementation(async (id) => trip(id));
  const view = renderHook(({ id }) => useTripPage(id), { initialProps: { id: "t1" } });
  await waitFor(() => expect(view.result.current.trip?.id).toBe("t1"));
  let complete!: (value: Trip) => void;
  let operation!: Promise<void>;
  act(() => { operation = view.result.current.run(() => new Promise((resolve) => { complete = resolve; })); });
  view.rerender({ id: "t2" });
  await waitFor(() => expect(view.result.current.trip?.id).toBe("t2"));
  await act(async () => { complete(trip("t1")); await operation; });
  expect(view.result.current.trip?.id).toBe("t2");
});

it("trocar carregamento limpa checklist e nomes quando o plano secundário falha", async () => {
  vi.mocked(getLoadingSession).mockImplementation(async (id) => ({ id, loadPlanId: id, status: "PENDING", startedAt: null, finishedAt: null, items: [{ id: "i1", loadPlanItemId: "pi1", code: "codigo", status: "PENDING" }] }));
  vi.mocked(getLoadPlan).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Sem permissão", [], 403));
  const view = renderHook(({ id }) => useLoadingSession(id), { initialProps: { id: "s1" } });
  await waitFor(() => expect(view.result.current.isLoading).toBe(false));
  expect(view.result.current.session?.id).toBe("s1");
  view.rerender({ id: "s2" });
  expect(view.result.current.session).toBeNull();
  expect(view.result.current.rows).toHaveLength(0);
  await waitFor(() => expect(view.result.current.isLoading).toBe(false));
  expect(view.result.current.session?.id).toBe("s2");
  expect(view.result.current.rows[0].product).toBeUndefined();
});
