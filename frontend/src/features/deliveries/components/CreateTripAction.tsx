import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { Modal } from "../../../components/Modal";
import { useResourceList } from "../../../hooks/useResourceList";
import { ApiError } from "../../../types/api";
import { listDriverOperationalStatus, listDrivers } from "../../drivers/api/driversApi";
import { createTrip } from "../api/tripsApi";
import { mapTripErrorToMessage } from "./tripsErrorMessages";

interface CreateTripActionProps {
  readonly loadPlanId: string;
  readonly onExistingTrip?: () => void;
}

/** Criação explícita pelo plano aprovado; conflito reconsulta os vínculos reais. */
export function CreateTripAction({ loadPlanId, onExistingTrip }: CreateTripActionProps) {
  const navigate = useNavigate();
  const { items: drivers } = useResourceList(listDrivers);
  const { items: driverStatuses, status: driverStatusesStatus } = useResourceList(
    listDriverOperationalStatus,
  );
  const [isOpen, setIsOpen] = useState(false);
  const [driverId, setDriverId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeDrivers = drivers.filter((driver) => driver.active);
  const statusByDriver = useMemo(
    () => new Map(driverStatuses.map((status) => [status.id, status])),
    [driverStatuses],
  );
  const selectedDriverUnavailable =
    driverId !== "" && statusByDriver.get(driverId)?.available === false;

  async function handleCreate() {
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const trip = await createTrip({ loadPlanId, driverId });
      navigate(`/trips/${trip.id}`);
    } catch (error) {
      if (error instanceof ApiError && error.code === "TRIP_LOAD_PLAN_ALREADY_ASSIGNED" && onExistingTrip) {
        onExistingTrip();
        return;
      }
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
              hint={
                driverStatusesStatus === "loading"
                  ? "Consultando a disponibilidade dos motoristas…"
                  : driverStatusesStatus === "error"
                    ? "Não foi possível confirmar a disponibilidade agora. O servidor fará a validação ao criar a viagem."
                    : "Motoristas em outra operação aparecem bloqueados conforme a disponibilidade informada pelo backend."
              }
            >
              <select id="trip-driver" value={driverId} onChange={(e) => setDriverId(e.target.value)}>
                <option value="">Selecione o motorista</option>
                {activeDrivers.map((driver) => {
                  const operationalStatus = statusByDriver.get(driver.id);
                  const unavailable = operationalStatus?.available === false;
                  const suffix = operationalStatus?.hasDocumentConflict ? " — documentação pendente" : operationalStatus?.hasOperationConflict
                    ? " — em operação"
                    : unavailable
                      ? " — indisponível"
                      : "";

                  return (
                    <option key={driver.id} value={driver.id} disabled={unavailable}>
                      {driver.name}
                      {driver.licenseCategory ? ` — CNH ${driver.licenseCategory}` : ""}
                      {suffix}
                    </option>
                  );
                })}
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
                disabled={driverId === "" || selectedDriverUnavailable || isSubmitting}
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
