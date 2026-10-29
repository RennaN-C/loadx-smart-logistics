import { lazy, Suspense, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { getLoadPlan } from "../load-planning/api/loadPlansApi";
import type { LoadPlan } from "../load-planning/types";
import { PLAN_STATUS_LABELS } from "../load-planning/components/loadPlanLabels";
import type { AssistantFact } from "./assistantApi";

const LoadViewer = lazy(() =>
  import("../load-visualization/components/LoadViewer").then((module) => ({ default: module.LoadViewer })),
);

type FactValue = string | number | null;
type Values = Record<string, FactValue>;
const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const percent = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

function metric(values: Values, key: string): number | null {
  const value = values[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
function rows(values: Values): string[] {
  return Object.entries(values)
    .filter(([key, value]) => /^item_\d+$/.test(key) && typeof value === "string")
    .sort(([a], [b]) => Number(a.slice(5)) - Number(b.slice(5)))
    .map(([, value]) => value as string);
}
function boundedPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}
function planReference(fact: AssistantFact): string | null {
  const path = (fact.links ?? []).find((link) => /^\/planning\/[0-9a-f-]{36}$/i.test(link.href))?.href;
  return path ? path.split("/").at(-1)! : null;
}

function PlanPreview({ planId }: { readonly planId: string }) {
  const [plan, setPlan] = useState<LoadPlan | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    getLoadPlan(planId).then((data) => {
      if (active) setPlan(data);
    }).catch(() => {
      if (active) setError(true);
    });
    return () => { active = false; };
  }, [planId]);

  if (error) return <p className="assistant-inline-note" role="alert">
    Não foi possível consultar a prévia autorizada. Abra o planejamento para ver o 3D completo.
  </p>;
  if (!plan) return <p className="assistant-inline-note" role="status">
    <span className="spinner" aria-hidden="true" /> Carregando dados autorizados do plano…
  </p>;
  return <>
    <p className="loxi-preview-hint">
      Prévia interativa · arraste para girar e use a rolagem para aproximar.
      <Link to={`/planning/${planId}`}>Visualização completa</Link>
    </p>
    <Suspense fallback={<p className="assistant-inline-note" role="status">Carregando visualizador 3D…</p>}>
      <LoadViewer planId={planId} plan={plan} />
    </Suspense>
  </>;
}

function PlanOperationalCard({ fact, onLink }: { readonly fact: AssistantFact; readonly onLink: () => void }) {
  const values = fact.values;
  const loaded = metric(values, "loaded_volumes");
  const rejected = metric(values, "rejected_volumes");
  const geometric = metric(values, "occupancy_percent");
  const utilization = metric(values, "weight_utilization_percent");
  const weight = metric(values, "weight_kg");
  const capacity = metric(values, "truck_capacity_weight_kg");
  const remaining = weight !== null && capacity !== null && capacity >= weight ? capacity - weight : null;
  const plate = typeof values.truck_plate === "string" ? values.truck_plate : "Planejamento salvo";
  const status = typeof values.status === "string"
    ? (PLAN_STATUS_LABELS[values.status as keyof typeof PLAN_STATUS_LABELS] ?? values.status) : "Salvo";
  const planId = planReference(fact);
  const [preview, setPreview] = useState(false);
  const insight = rejected === 0 && geometric !== null && utilization !== null
    ? utilization > geometric + 15
      ? "Todos os volumes foram posicionados. A capacidade de peso está proporcionalmente mais utilizada que o espaço do baú."
      : "Todos os volumes foram posicionados. Confira peso e espaço antes de aprovar a operação."
    : "Os indicadores são do cálculo salvo. Consulte as rejeições e a sequência antes de tomar decisões.";
  return <section className="loxi-operational-card loxi-plan-card" aria-label="Resumo visual do planejamento">
    <header className="loxi-card-header">
      <div><span className="loxi-eyebrow"><Icon name="planning" size={14} /> Planejamento salvo</span>
        <strong>{plate}</strong></div>
      <span className="loxi-status-chip">{status}</span>
    </header>
    <div className="loxi-plan-kpis">
      <div><strong>{loaded === null ? "—" : number.format(loaded)}</strong><span>Volumes carregados</span></div>
      <div><strong>{rejected === null ? "—" : number.format(rejected)}</strong><span>Volumes rejeitados</span></div>
    </div>
    {([
      ["Utilização de peso", utilization, "weight"],
      ["Ocupação geométrica", geometric, "space"],
    ] as const).map(([label, value, tone]) => value !== null && <div className="loxi-meter" key={tone}>
      <div className="loxi-meter-head"><span>{label}</span><strong>{percent.format(value)}<span>%</span></strong></div>
      <div className="loxi-meter-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={boundedPercent(value)}>
        <div className={`loxi-meter-fill loxi-meter-${tone}`} style={{ width: `${boundedPercent(value)}%` }} />
      </div>
      {tone === "weight" && weight !== null && capacity !== null
        ? <small>{number.format(weight)} de {number.format(capacity)} kg{remaining !== null ? ` · ${number.format(remaining)} kg restantes` : ""}</small>
        : <small>Percentual registrado no cálculo persistido</small>}
    </div>)}
    <div className="loxi-insight"><Icon name="gauge" size={16} /><p>{insight} Nenhuma simulação nova foi executada pelo chat.</p></div>
    {planId ? <div className="loxi-card-actions">
      <button type="button" className="loxi-action" onClick={() => setPreview((old) => !old)} aria-expanded={preview}>
        <Icon name="planning" size={15} /> {preview ? "Fechar prévia 3D" : "Explorar carga em 3D"}
      </button>
      <Link to={`/planning/${planId}`} onClick={onLink}>Abrir plano <Icon name="arrow-right" size={14} /></Link>
    </div> : null}
    {preview && planId ? <div className="loxi-preview"><PlanPreview key={planId} planId={planId} /></div> : null}
  </section>;
}

function parseTruck(value: string): { name: string; plate: string; reason: string } {
  const parts = value.split(" · ");
  const platePart = parts.find((part) => part.startsWith("placa "));
  return {
    name: parts[0] ?? "Caminhão",
    plate: platePart?.slice(6) ?? "Placa não informada",
    reason: parts.filter((part) => part !== parts[0] && part !== platePart).join(" · "),
  };
}
function FleetOperationalCard({ fact, onLink, unavailable }: {
  readonly fact: AssistantFact; readonly onLink: () => void; readonly unavailable: boolean;
}) {
  const values = fact.values;
  const total = metric(values, unavailable ? "page_vehicle_count" : "total_records");
  const inactive = metric(values, "page_unavailable_count");
  const available = total !== null && inactive !== null ? Math.max(0, total - inactive) : null;
  const items = rows(values);
  const page = metric(values, "page");
  const pages = metric(values, "total_pages");
  return <section className="loxi-operational-card loxi-fleet-card" aria-label={unavailable ? "Disponibilidade operacional da frota" : "Caminhões cadastrados"}>
    <header className="loxi-card-header">
      <div><span className="loxi-eyebrow"><Icon name="truck" size={14} /> Loxi · Frota</span>
        <strong>{unavailable ? "Disponibilidade operacional" : "Caminhões cadastrados"}</strong></div>
    </header>
    <div className="loxi-fleet-kpis">
      <div><strong>{total === null ? "—" : number.format(total)}</strong><span>{unavailable ? "Nesta página" : "Cadastrados"}</span></div>
      {unavailable && <><div><strong>{available === null ? "—" : number.format(available)}</strong><span>Disponíveis</span></div>
        <div><strong>{inactive === null ? "—" : number.format(inactive)}</strong><span>Indisponíveis</span></div></>}
    </div>
    <div className="loxi-vehicle-list">
      {items.length ? items.map((item, i) => {
        const truck = parseTruck(item);
        const reason = unavailable ? truck.reason : (truck.reason || "Situação não informada");
        const restricted = /arquivad|manuten|document|opera|indispon/i.test(reason.normalize("NFD").replace(/[\u0300-\u036f]/g, ""));
        return <div className="loxi-vehicle" key={i}>
          <span className="loxi-vehicle-icon"><Icon name="truck" size={17}/></span>
          <div className="loxi-vehicle-info"><strong>{truck.name} · {truck.plate}</strong>
            <span className={restricted ? "loxi-vehicle-state is-restricted" : "loxi-vehicle-state"}>{reason}</span></div>
        </div>;
      }) : <p className="assistant-inline-note">Nenhum registro nesta página.</p>}
    </div>
    {pages !== null && pages > 1 ? <p className="loxi-page-note">Página {page ?? 1} de {pages} · Outros registros podem estar nas próximas páginas.</p> : null}
    {unavailable ? <p className="loxi-page-note">Ativo no cadastro não significa disponível para operar.</p> : null}
    <div className="loxi-card-actions">
      <Link to={unavailable ? "/trucks?tab=availability" : "/trucks"} onClick={onLink}>
        {unavailable ? "Consultar disponibilidade" : "Abrir frota"} <Icon name="arrow-right" size={14}/>
      </Link>
    </div>
  </section>;
}

const RECORD_ROUTES: Record<string, string> = {
  "Pedidos cadastrados": "/orders",
  "Produtos cadastrados": "/products",
  "Clientes cadastrados": "/contacts?tab=customers",
  "Motoristas cadastrados": "/contacts?tab=drivers",
};

function RecordOperationalCard({ fact, onLink }: { readonly fact: AssistantFact; readonly onLink: () => void }) {
  const values = fact.values;
  const count = metric(values, "total_records");
  const page = metric(values, "page");
  const pages = metric(values, "total_pages");
  const items = rows(values);
  const route = RECORD_ROUTES[fact.name];
  const label = (fact.links ?? []).find((link) => link.href === route)?.label
    ?? "Consultar " + fact.name.toLowerCase();
  return <section className="loxi-operational-card loxi-records-card" aria-label={fact.name}>
    <header className="loxi-card-header">
      <div><span className="loxi-eyebrow"><Icon name="chart" size={14} /> Loxi · Cadastros</span>
        <strong>{fact.name}</strong></div>
      {count !== null ? <span className="loxi-status-chip">{number.format(count)} no total</span> : null}
    </header>
    <div className="loxi-vehicle-list">
      {items.map((item, index) => {
        const parts = item.split(" · ");
        return <div className="loxi-vehicle" key={index}>
          <span className="loxi-vehicle-icon"><Icon name="report" size={17} /></span>
          <div className="loxi-vehicle-info"><strong>{parts[0]}</strong>
            {parts.slice(1).length ? <span className="loxi-vehicle-state">{parts.slice(1).join(" · ")}</span> : null}</div>
        </div>;
      })}
      {!items.length ? <p className="assistant-inline-note">Nenhum registro nesta página.</p> : null}
    </div>
    {pages !== null && pages > 1 ? <p className="loxi-page-note">Página {page ?? 1} de {pages}. Mais resultados estão disponíveis na tela.</p> : null}
    <div className="loxi-card-actions">
      <Link to={route} onClick={onLink}>{label} <Icon name="arrow-right" size={14} /></Link>
    </div>
  </section>;
}

/** Only known backend Source names activate rich cards; no model-controlled layout. */
export function AssistantOperationalCard({ fact, onLink }: {
  readonly fact: AssistantFact; readonly onLink: () => void;
}) {
  if (fact.name === "Análise do planejamento" || fact.name === "Plano autorizado")
    return <PlanOperationalCard fact={fact} onLink={onLink} />;
  if (fact.name === "Disponibilidade atual da frota")
    return <FleetOperationalCard fact={fact} onLink={onLink} unavailable />;
  if (fact.name === "Caminhões cadastrados")
    return <FleetOperationalCard fact={fact} onLink={onLink} unavailable={false} />;
  if (fact.name in RECORD_ROUTES)
    return <RecordOperationalCard fact={fact} onLink={onLink} />;
  return null;
}

export function hasOperationalCard(fact: AssistantFact): boolean {
  return ["Análise do planejamento", "Plano autorizado", "Disponibilidade atual da frota", "Caminhões cadastrados"].includes(fact.name)
    || fact.name in RECORD_ROUTES;
}

/** The card owns these navigation targets, even when Source.links is empty. */
export function operationalCardDestination(fact: AssistantFact): string | null {
  if (fact.name === "Disponibilidade atual da frota") return "/trucks?tab=availability";
  if (fact.name === "Caminhões cadastrados") return "/trucks";
  return RECORD_ROUTES[fact.name] ?? null;
}
