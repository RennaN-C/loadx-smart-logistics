import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { FleetStatusPage } from "./FleetStatusPage";
import { TruckListPage } from "./TruckListPage";
import "./TruckWorkspacePage.css";

export function TruckWorkspacePage() {
  const { search } = useLocation();
  const availability = new URLSearchParams(search).get("tab") === "availability";
  const [availabilityVisited, setAvailabilityVisited] = useState(availability);
  useEffect(() => { if (availability) setAvailabilityVisited(true); }, [availability]);
  return <div className="entity-page truck-workspace">
    <header className="entity-header"><div><h1>Caminhões e frota</h1><p className="entity-lede">Gerencie os veículos e consulte a disponibilidade da operação.</p></div></header>
    <nav className="truck-workspace-tabs" aria-label="Seções de caminhões e frota">
      <Link to="/trucks" aria-current={!availability ? "location" : undefined}>Veículos</Link>
      <Link to="/trucks?tab=availability" aria-current={availability ? "location" : undefined}>Disponibilidade</Link>
    </nav>
    <section aria-label="Veículos" hidden={availability}><TruckListPage embedded active={!availability} /></section>
    <section aria-label="Disponibilidade" hidden={!availability}>{availabilityVisited && <FleetStatusPage embedded />}</section>
  </div>;
}
