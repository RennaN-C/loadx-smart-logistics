import { useEffect, useState } from "react";
import { preflightDistribution } from "../api/distributionsApi";
import type { DistributionNeed } from "../types";
import { DistributionFeedback } from "./DistributionFeedback";

export function FleetPreflight({ orderIds }: { readonly orderIds: readonly string[] }) {
  const selection = [...orderIds].sort((a, b) => a.localeCompare(b)).join(",");
  const [need, setNeed] = useState<DistributionNeed | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setNeed(null); setError(null);
    if (selection) preflightDistribution(selection.split(",")).then((result) => { if (active) setNeed(result); }).catch((reason) => { if (active) setError(reason); });
    return () => { active = false; };
  }, [selection, attempt]);
  if (!selection) return <p>Selecione os pedidos para consultar a frota elegível.</p>;
  if (error) return <div><DistributionFeedback error={error} /><button className="btn-secondary" type="button" onClick={() => setAttempt((value) => value + 1)}>Consultar frota novamente</button></div>;
  if (!need) return <p role="status">Consultando a elegibilidade da frota…</p>;
  return <section className="fleet-preflight" aria-label="Frota para distribuição automática">
    <p><strong>{need.eligibleTrucks.length} caminhão(ões) elegível(is)</strong> · {need.volumes.length} volumes nesta necessidade.</p>
    <p className="entity-form-help">A distribuição usa quantos veículos forem necessários, de 1 a 10, para acomodar toda a carga. Cargas que cabem em um veículo podem gerar uma única parte.</p>
    {need.eligibleTrucks.length === 0 ? <p role="alert">Nenhum caminhão elegível. Revise a disponibilidade, a manutenção e a documentação da frota antes de calcular.</p> : <ul>{need.eligibleTrucks.map((truck) => <li key={truck.id}><strong>{truck.plate}</strong><span>{truck.model}</span><small>{truck.maxWeightKg.toLocaleString("pt-BR")} kg · {truck.lengthCm} × {truck.widthCm} × {truck.heightCm} cm</small></li>)}</ul>}
    {need.ineligibleTrucks.length > 0 ? <p className="entity-form-help">{need.ineligibleTrucks.length} veículo(s) excluído(s) pelo servidor por indisponibilidade ou pendência.</p> : null}
  </section>;
}
