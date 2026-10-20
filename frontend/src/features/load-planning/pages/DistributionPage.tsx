import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { AlertBanner } from "../../../components/AlertBanner";
import { useAuth } from "../../auth/hooks/useAuth";
import { hasPermission } from "../../auth/permissions";
import { distributionAction, getDistribution, reprocessDistributionPart } from "../api/distributionsApi";
import { DistributionFeedback } from "../components/DistributionFeedback";
import { DistributionOverview } from "../components/DistributionOverview";
import { DistributionDetail } from "../components/DistributionDetail";
import { DistributionVehicles } from "../components/DistributionVehicles";
import type { LoadDistribution } from "../types";
import "./PlanningPage.css";
import "./DistributionPage.css";

function DistributionWorkspace({ id }: { readonly id: string }) {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [stored, setStored] = useState<LoadDistribution | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [refreshRequired, setRefreshRequired] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [success, setSuccess] = useState("");
  const pending = useRef(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const canRead = hasPermission(user, "loadx.planning.read");
  const canApprove = hasPermission(user, "loadx.planning.approve");
  const canCreate = hasPermission(user, "loadx.planning.create");
  useEffect(() => {
    if (!canRead) return;
    let active = true;
    setLoading(true); setError(null);
    getDistribution(id).then((result) => {
      if (active) { setStored(result); setRefreshRequired(false); }
    }).catch((error_) => { if (active) setError(error_); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, attempt, canRead, user?.role]);
  const distribution = stored && (user?.role !== "CHECKER" || stored.status === "APPROVED") ? stored : null;
  const part = distribution?.parts.find((p) => p.id === params.get("part")) ?? distribution?.parts[0];
  async function mutate(action: () => Promise<LoadDistribution>) {
    if (pending.current) return;
    pending.current = true; setWorking(true); setError(null); setSuccess("");
    try {
      const result = await action();
      if (alive.current) { setStored(result); setSuccess("Distribuição atualizada e salva."); }
    } catch (error_) {
      if (alive.current) { setError(error_); setRefreshRequired(true); }
    } finally {
      pending.current = false;
      if (alive.current) setWorking(false);
    }
  }
  if (!canRead) return <AlertBanner>Seu perfil não tem acesso ao planejamento.</AlertBanner>;
  const disabled = working || loading || refreshRequired;
  return <>
    <DistributionFeedback error={error} />
    {error ? <button type="button" className="btn-secondary" disabled={working || loading} onClick={() => setAttempt((value) => value + 1)}>Atualizar distribuição</button> : null}
    {refreshRequired ? <p className="entity-form-help">A proposta foi mantida. Consulte o estado atual antes de repetir uma ação.</p> : null}
    {success ? <output className="distribution-success">{success}</output> : null}
    {loading ? <output className="entity-state"><span className="spinner" aria-hidden="true" />Carregando distribuição…</output> : null}
    {distribution && part ? <>
      <DistributionOverview distribution={distribution} canApprove={canApprove} working={working} disabled={disabled}
        onAction={(action) => void mutate(() => distributionAction(id, action))} />
      <DistributionVehicles parts={distribution.parts} selectedId={part.id} onSelect={(partId) => { const next = new URLSearchParams(params); next.set("part", partId); setParams(next); }} />
      <DistributionDetail distribution={distribution} part={part} canApprove={canApprove} canCreate={canCreate} disabled={disabled}
        onAction={(action, partId) => void mutate(() => distributionAction(id, action, partId))}
        onReprocess={(truckId) => void mutate(() => reprocessDistributionPart(id, part.id, truckId, part.loadPlan.id))} />
    </> : null}
  </>;
}
export function DistributionPage() {
  const { distributionId } = useParams<{ distributionId: string }>();
  return <div className="entity-page distribution-page">
    <nav className="entity-toolbar entity-page-nav" aria-label="Caminhos da distribuição"><Link to="/planning">Voltar aos planos existentes</Link><Link to="/orders">Voltar aos pedidos</Link></nav>
    <header className="entity-header"><div><h1>Distribuição de carga</h1><p className="entity-lede">Acompanhe a necessidade completa e inspecione a carga de cada veículo.</p></div></header>
    {distributionId ? <DistributionWorkspace key={distributionId} id={distributionId} /> : null}
  </div>;
}
