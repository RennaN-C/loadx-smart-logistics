import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { Modal } from "../../../components/Modal";
import { useResourceList } from "../../../hooks/useResourceList";
import { ApiError } from "../../../types/api";
import { listDrivers } from "../../drivers/api/driversApi";
import { createTrip } from "../api/tripsApi";
import { mapTripErrorToMessage } from "./tripsErrorMessages";

interface CreateTripActionProps {
  readonly loadPlanId: string;
}

/**
 * Único caminho para criar viagem: o plano aprovado. O backend não lista viagens
 * nem planos, então a navegação precisa partir daqui — depois de criada, a
 * viagem vive em `/trips/:tripId`.
 */
export function CreateTripAction({ loadPlanId }: CreateTripActionProps) {
  const navigate = useNavigate();
  const { items: drivers } = useResourceList(listDrivers);
  const [isOpen, setIsOpen] = useState(false);
  const [driverId, setDriverId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeDrivers = drivers.filter((driver) => driver.active);

  async function handleCreate() {
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const trip = await createTrip({ loadPlanId, driverId });
      navigate(`/trips/${trip.id}`);
    } catch (error) {
      setErrorMessage(
        mapTripErrorToMessage(
          error instanceof ApiError
            ? error
            : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
        ),
      );
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <button type="button" className="btn-primary" onClick={() => setIsOpen(true)}>
        Criar viagem
      </button>

      {isOpen ? (
        <Modal title="Nova viagem" subtitle="A partir deste plano" onClose={() => setIsOpen(false)}>
          <div className="entity-form">
            {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

            <FormField
              id="trip-driver"
              label="MOTORISTA"
              hint="Só motoristas ativos podem assumir uma viagem."
            >
              <select id="trip-driver" value={driverId} onChange={(e) => setDriverId(e.target.value)}>
                <option value="">Selecione o motorista</option>
                {activeDrivers.map((driver) => (
                  <option key={driver.id} value={driver.id}>
                    {driver.name}
                    {driver.licenseCategory ? ` — CNH ${driver.licenseCategory}` : ""}
                  </option>
                ))}
              </select>
            </FormField>

            <p className="entity-form-help">
              As paradas da viagem saem dos pedidos do plano, na ordem de entrega já calculada.
            </p>

            <div className="entity-form-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setIsOpen(false)}
                disabled={isSubmitting}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={driverId === "" || isSubmitting}
                onClick={() => void handleCreate()}
              >
                {isSubmitting ? (
                  <>
                    <span className="spinner" aria-hidden="true" />
                    <span>Criando…</span>
                  </>
                ) : (
                  <span>Criar viagem</span>
                )}
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
