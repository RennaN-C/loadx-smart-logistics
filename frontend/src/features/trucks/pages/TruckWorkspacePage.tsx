import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { FleetStatusPage } from "./FleetStatusPage";
import { FleetDocumentsPage } from "./FleetDocumentsPage";
import { TruckListPage } from "./TruckListPage";
import "../../../components/RegistryTable.css";
import "./TruckWorkspacePage.css";

export function TruckWorkspacePage() {
  const { search } = useLocation();
  const tab = new URLSearchParams(search).get("tab");
  const availability = tab === "availability";
  const documents = tab === "documents";
  const [availabilityVisited, setAvailabilityVisited] = useState(availability);
  const [documentsVisited, setDocumentsVisited] = useState(documents);
  useEffect(() => { if (availability) setAvailabilityVisited(true); }, [availability]);
  useEffect(() => { if (documents) setDocumentsVisited(true); }, [documents]);
  const title = availability ? "Disponibilidade da frota" : documents ? "Documentos da frota" : "Caminhões e frota";
  const description = availability
    ? "Veja quais veículos podem ser usados no planejamento."
    : documents
      ? "Acompanhe a validade e o histórico documental por veículo."
      : "Gerencie veículos e consulte sua disponibilidade operacional.";
  return <div className="entity-page truck-workspace">
    <header className="entity-header"><div><p className="truck-workspace-eyebrow">Cadastros</p><h1>{title}</h1><p className="entity-lede">{description}</p></div></header>
    <nav className="truck-workspace-tabs" aria-label="Seções de caminhões e frota">
      <Link to="/trucks" aria-current={!availability && !documents ? "location" : undefined}>Veículos</Link>
      <Link to="/trucks?tab=availability" aria-current={availability ? "location" : undefined}>Disponibilidade</Link>
      <Link to="/trucks?tab=documents" aria-current={documents ? "location" : undefined}>Documentação</Link>
    </nav>
    <section aria-label="Veículos" hidden={availability || documents}><TruckListPage embedded active={!availability && !documents} /></section>
    <section aria-label="Disponibilidade" hidden={!availability}>{availabilityVisited && <FleetStatusPage embedded />}</section>
    <section aria-label="Documentação" hidden={!documents}>{documentsVisited && <FleetDocumentsPage />}</section>
  </div>;
}
