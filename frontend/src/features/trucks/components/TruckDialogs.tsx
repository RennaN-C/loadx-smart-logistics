import { Modal } from "../../../components/Modal";
import type { Truck } from "../types";
import { DocumentsPanel } from "./DocumentsPanel";
import { MaintenancePanel } from "./MaintenancePanel";
import { TruckForm } from "./TruckForm";

interface TruckDialogsProps {
  readonly active: boolean;
  readonly documentsTruck: Truck | null;
  readonly maintenanceTruck: Truck | null;
  readonly editingTruck: Truck | null;
  readonly isCreating: boolean;
  readonly onCloseDocuments: () => void;
  readonly onCloseMaintenance: () => void;
  readonly onCloseForm: () => void;
  readonly onChanged: () => Promise<void>;
  readonly onSaved: () => Promise<void>;
}

export function TruckDialogs({ active, documentsTruck, maintenanceTruck, editingTruck, isCreating, onCloseDocuments, onCloseMaintenance, onCloseForm, onChanged, onSaved }: TruckDialogsProps) {
  const isFormOpen = isCreating || editingTruck !== null;
  return <>
      {documentsTruck ? <Modal active={active} title={`Documentos — ${documentsTruck.plate}`} onClose={onCloseDocuments}>
        <DocumentsPanel truck={documentsTruck} onChanged={onChanged} />
      </Modal> : null}
      {maintenanceTruck ? <Modal active={active} title={`Manutenções — ${maintenanceTruck.plate}`} onClose={onCloseMaintenance}>
        <MaintenancePanel truck={maintenanceTruck} onChanged={onChanged} />
      </Modal> : null}

      {isFormOpen ? (
        <Modal
          active={active}
          title={editingTruck ? "Editar caminhão" : "Novo caminhão"}
          subtitle="Compartimento de carga"
          onClose={onCloseForm}
        >
          <TruckForm truck={editingTruck ?? undefined} onSaved={onSaved} onCancel={onCloseForm} />
        </Modal>
      ) : null}
  </>;
}
