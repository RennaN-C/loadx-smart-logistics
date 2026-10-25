import { useEffect, useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { useResourceList } from "../../../hooks/useResourceList";
import { listTrucks } from "../api/trucksApi";
import { DocumentsPanel } from "../components/DocumentsPanel";
import { mapTruckErrorToMessage } from "../components/trucksErrorMessages";

export function FleetDocumentsPage() {
  const { items, status, error, refetch } = useResourceList(listTrucks);
  const [selectedId, setSelectedId] = useState("");
  useEffect(() => {
    if (items.length > 0 && !items.some((truck) => truck.id === selectedId)) setSelectedId(items[0].id);
  }, [items, selectedId]);
  const selectedTruck = useMemo(() => items.find((truck) => truck.id === selectedId) ?? null, [items, selectedId]);

  return <div className="fleet-documents-page">
    <div className="fleet-documents-filter">
      <label htmlFor="fleet-document-truck">Veículo</label>
      <select id="fleet-document-truck" value={selectedId} onChange={(event) => setSelectedId(event.target.value)} disabled={status !== "success" || items.length === 0}>
        {items.length === 0 ? <option value="">Nenhum veículo disponível</option> : items.map((truck) => <option key={truck.id} value={truck.id}>{truck.plate} · {truck.model}</option>)}
      </select>
      <p>O contrato atual consulta documentos por veículo. Selecione um cadastro para acessar seu histórico real.</p>
    </div>
    {status === "loading" ? <p className="entity-state"><span className="spinner" aria-hidden="true" />Carregando veículos…</p> : null}
    {status === "error" && error ? <div className="fleet-documents-error"><AlertBanner>{mapTruckErrorToMessage(error)}</AlertBanner><button type="button" className="btn-secondary" onClick={() => void refetch()}>Tentar novamente</button></div> : null}
    {status === "success" && items.length === 0 ? <p className="entity-state">Cadastre um veículo antes de registrar documentos.</p> : null}
    {selectedTruck ? <DocumentsPanel truck={selectedTruck} onChanged={refetch} /> : null}
  </div>;
}
