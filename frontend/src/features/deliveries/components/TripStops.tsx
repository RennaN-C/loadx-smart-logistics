import { useState } from "react";

import { Modal } from "../../../components/Modal";
import { StatusPill } from "../../../components/StatusPill";
import { DeliveryCommunicationPanel } from "./DeliveryCommunicationPanel";
import { DeliveryEvidencePanel } from "./DeliveryEvidencePanel";
import {
  DELIVERY_ACTION_LABELS,
  DELIVERY_STATUS_LABELS,
  deliveryStatusTone,
} from "./tripLabels";
import { DELIVERY_TRANSITIONS, type Delivery, type Trip } from "../types";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

interface TripStopProps {
  readonly delivery: Delivery;
  /** Já resolvido por quem chama: perfil pode operar E a viagem está em rota. */
  readonly canAdvance: boolean;
  readonly isWorking: boolean;
  readonly onAdvance: (delivery: Delivery, next: Delivery["status"]) => void;
  readonly onOpenReceipt: (delivery: Delivery) => void;
  readonly onOpenCommunication: (delivery: Delivery) => void;
  readonly canReadReceipts: boolean;
  readonly canReadCommunication: boolean;
}

function TripStop({ delivery, canAdvance, isWorking, onAdvance, onOpenReceipt, onOpenCommunication, canReadReceipts, canReadCommunication }: TripStopProps) {
  const next = DELIVERY_TRANSITIONS[delivery.status];

  return (
    <li className="trip-stop">
      <span className="trip-stop-seq">{delivery.sequence}</span>
      <div className="trip-stop-body">
        <StatusPill tone={deliveryStatusTone(delivery.status)}>
          {DELIVERY_STATUS_LABELS[delivery.status]}
        </StatusPill>
        {delivery.deliveredAt ? (
          <span className="trip-stop-time">
            entregue em {dateTime.format(new Date(delivery.deliveredAt))}
          </span>
        ) : null}
      </div>
      {/* O comprovante nasce da CONCLUSÃO: antes dela o backend recusa, então
          o botão só aparece quando há o que mostrar. */}
      {canReadCommunication && <button type="button" className="btn-secondary" aria-label={`Comunicação da parada ${delivery.sequence}`} onClick={() => onOpenCommunication(delivery)}>Comunicação</button>}
      {canReadReceipts && delivery.status === "DELIVERED" ? (
        <button
          type="button"
          className="btn-secondary"
          aria-label={`Comprovante da parada ${delivery.sequence}`}
          onClick={() => onOpenReceipt(delivery)}
        >
          Comprovante
        </button>
      ) : null}
      {next ? (
        <button
          type="button"
          className="btn-secondary"
          disabled={!canAdvance || isWorking}
          onClick={() => onAdvance(delivery, next)}
        >
          {DELIVERY_ACTION_LABELS[delivery.status]}
        </button>
      ) : null}
    </li>
  );
}

interface TripStopsProps {
  readonly canReadReceipts?: boolean;
  readonly canReadCommunication?: boolean;
  readonly trip: Trip;
  readonly canOperate: boolean;
  readonly isWorking: boolean;
  readonly onAdvance: (delivery: Delivery, next: Delivery["status"]) => void;
}

/**
 * As paradas na ordem de descarga.
 *
 * A ordenação é feita numa cópia: `sort` altera o array no lugar, e mexer no
 * que veio da resposta faria a lista mudar de ordem em rerenders futuros.
 */
export function TripStops({ trip, canOperate, isWorking, onAdvance, canReadReceipts = true, canReadCommunication = false }: TripStopsProps) {
  const inRoute = trip.status === "IN_ROUTE";
  const [communicationOf, setCommunicationOf] = useState<Delivery | null>(null);
  const [receiptOf, setReceiptOf] = useState<Delivery | null>(null);

  return (
    <>
    <ol className="trip-stops">
      {[...trip.deliveries]
        .sort((a, b) => a.sequence - b.sequence)
        .map((delivery) => (
          <TripStop
            key={delivery.id}
            delivery={delivery}
            canAdvance={canOperate && inRoute}
            isWorking={isWorking}
            onAdvance={onAdvance}
            onOpenReceipt={setReceiptOf}
            onOpenCommunication={setCommunicationOf}
            canReadReceipts={canReadReceipts}
            canReadCommunication={canReadCommunication}
          />
        ))}
    </ol>

    {communicationOf && <Modal title={`Comunicação — parada ${communicationOf.sequence}`} subtitle="Fatos vinculados à entrega e estado do canal simulado" onClose={() => setCommunicationOf(null)}><DeliveryCommunicationPanel deliveryId={communicationOf.id} /></Modal>}
    {receiptOf ? (
      <Modal
        title={`Comprovante — parada ${receiptOf.sequence}`}
        subtitle="Conclusão registrada e evidências ligadas a ela"
        onClose={() => setReceiptOf(null)}
      >
        <DeliveryEvidencePanel deliveryId={receiptOf.id} canOperate={canOperate} />
      </Modal>
    ) : null}
    </>
  );
}
