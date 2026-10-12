import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { CreateTripAction } from "../../deliveries/components/CreateTripAction";
import { StartLoadingAction } from "../../loading-operation/components/StartLoadingAction";
import { getLoadPlanContinuity } from "../api/loadPlansApi";
import type { LoadPlanContinuity } from "../types";

function ContinuityActions({ data, planId, canManage, refresh }: {
  readonly data: LoadPlanContinuity;
  readonly planId: string;
  readonly canManage: boolean;
  readonly refresh: () => void;
}) {
  const loadingAction = data.loading_session
    ? <Link className="btn-secondary" to={`/loading/${data.loading_session.id}`}>Abrir carregamento existente</Link>
    : canManage && data.operational_ready && <StartLoadingAction loadPlanId={planId} />;
  const tripAction = data.trip
    ? <Link className="btn-primary" to={`/trips/${data.trip.id}`}>Abrir viagem existente</Link>
    : data.operational_ready && <CreateTripAction loadPlanId={planId} onExistingTrip={refresh} />;
  return <div className="entity-form-actions">{loadingAction}{canManage ? tripAction : null}</div>;
}

/** Read persisted links before offering creation; failure never means absence. */
export function PlanContinuity({ planId, canManage }: {
  readonly planId: string; readonly canManage: boolean;
}) {
  const [data, setData] = useState<LoadPlanContinuity | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setData(null);
    setFailed(false);
    getLoadPlanContinuity(planId).then((result) => {
      if (active) setData(result);
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [planId, attempt]);

  if (failed) return <div className="plan-continuity">
    <AlertBanner>Não foi possível consultar a continuidade deste plano. Nenhuma operação foi criada.</AlertBanner>
    <button className="btn-secondary" type="button" onClick={() => setAttempt((value) => value + 1)}>Tentar novamente</button>
  </div>;
  if (!data) return <p className="entity-state" role="status">Consultando carregamento e viagem…</p>;
  return <section className="plan-continuity" aria-label="Continuidade da operação">
    <h3>Próxima etapa</h3>
    <p className="entity-form-help">O plano está aprovado. Carregamento e viagem têm estados próprios; concluir a conferência libera o início da viagem.</p>
    <ContinuityActions data={data} planId={planId} canManage={canManage} refresh={() => { setData(null); setAttempt((value) => value + 1); }} />
    {data.loading_session ? <Link className="btn-secondary" to={`/loading/${data.loading_session.id}`}>Abrir carregamento existente</Link>
        : canManage && data.operational_ready ? <StartLoadingAction loadPlanId={planId} /> : null}
      {canManage && data.trip ? <Link className="btn-primary" to={`/trips/${data.trip.id}`}>Abrir viagem existente</Link>
        : canManage && data.operational_ready ? <CreateTripAction loadPlanId={planId} onExistingTrip={() => { setData(null); setAttempt((value) => value + 1); }} /> : null}
    </div>
    {data.loading_session ? <p className="entity-form-help">Carregamento: {({ PENDING: "pendente", IN_PROGRESS: "em andamento", FINISHED: "concluído" })[data.loading_session.status]}.</p> : null}
    {data.trip ? <p className="entity-form-help">Viagem: {({ SCHEDULED: "programada", IN_ROUTE: "em rota", FINISHED: "concluída" })[data.trip.status]}.</p> : null}
    {!data.operational_ready ? <p className="entity-form-help">Este plano não está liberado para iniciar outra operação. As regras da distribuição são conferidas pelo servidor.</p> : null}
    {!canManage && !data.loading_session ? <p className="entity-form-help">O responsável logístico precisa iniciar o carregamento para disponibilizar a conferência.</p> : null}
  </section>;
}
