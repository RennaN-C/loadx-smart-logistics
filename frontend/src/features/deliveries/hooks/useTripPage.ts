import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../types/api";
import { getTrip } from "../api/tripsApi";
import { mapTripErrorToMessage } from "../components/tripsErrorMessages";
import type { Trip } from "../types";

export interface UseTripPageResult {
  readonly trip: Trip | null;
  readonly isLoading: boolean;
  /** Uma transição está em curso; trava os botões para não disparar duas vezes. */
  readonly isWorking: boolean;
  readonly errorMessage: string | null;
  /** Executa uma transição e guarda a viagem devolvida pelo backend. */
  readonly run: (action: () => Promise<Trip>) => Promise<void>;
}

/**
 * Carregamento e transições da viagem, fora do componente de tela.
 *
 * A tela só desenha; quem fala com a API é este hook. Toda transição devolve a
 * viagem inteira, e é ela que substitui o estado — nunca uma remontagem local
 * do que mudou, que poderia divergir do que o backend gravou.
 */
export function useTripPage(tripId: string | undefined): UseTripPageResult {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const toMessage = useCallback(
    (error: unknown) =>
      mapTripErrorToMessage(
        error instanceof ApiError
          ? error
          : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
      ),
    [],
  );

  useEffect(() => {
    if (!tripId) return;

    let active = true;
    setIsLoading(true);
    setErrorMessage(null);

    getTrip(tripId)
      .then((loaded) => {
        if (active) setTrip(loaded);
      })
      .catch((error) => {
        if (active) setErrorMessage(toMessage(error));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [toMessage, tripId]);

  const run = useCallback(
    async (action: () => Promise<Trip>) => {
      setErrorMessage(null);
      setIsWorking(true);

      try {
        setTrip(await action());
      } catch (error) {
        setErrorMessage(toMessage(error));
      } finally {
        setIsWorking(false);
      }
    },
    [toMessage],
  );

  return { trip, isLoading, isWorking, errorMessage, run };
}
