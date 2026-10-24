import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Icon, type IconName } from "../../../components/Icon";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { useAuth } from "../../auth/hooks/useAuth";
import { hasPermission } from "../../auth/permissions";
import { listCustomers } from "../../customers/api/customersApi";
import { getOperationalIndicators } from "../../operations/api/operationalIndicatorsApi";
import type { OperationalIndicators } from "../../operations/types";
import { STATUS_LABELS, priorityLabel, statusTone } from "../../orders/components/orderLabels";
import { DriverTrips } from "../components/DriverTrips";
import { useDashboardTotals } from "../hooks/useDashboardTotals";
import "./DashboardPage.css";

const dateFormatter = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });
const numberFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

interface CounterProps {
  readonly label: string;
  readonly value: number | null;
  readonly to: string;
  readonly icon: IconName;
  readonly description: string;
}

function Counter({ label, value, to, icon, description }: CounterProps) {
  return <Link className="kpi" to={to}>
    <span className="kpi-icon"><Icon name={icon} size={20} /></span>
    <span className="kpi-content"><span className="kpi-label">{label}</span><span className="kpi-value">{value ?? "—"}</span><span className="kpi-description">{description}</span></span>
  </Link>;
}

const listHistoricalCustomers = (params: ListParams) => listCustomers({ ...params, archiveStatus: "all" });

function useOperationalSnapshot(enabled: boolean) {
  const [data, setData] = useState<OperationalIndicators | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    setFailed(false);
    getOperationalIndicators().then((result) => { if (active) setData(result); }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [enabled, attempt]);
  return { data, failed, retry: useCallback(() => setAttempt((value) => value + 1), []) };
}

function ComparisonChart({ orders, deliveries }: { readonly orders: number; readonly deliveries: number }) {
  const max = Math.max(orders, deliveries, 1);
  return <section className="overview-panel overview-comparison" aria-labelledby="overview-comparison-title">
    <div className="overview-panel-heading">
      <div><h2 id="overview-comparison-title">Pedidos e entregas</h2><p>Totais persistidos desde o início</p></div>
      <ul className="overview-legend"><li><i data-series="orders" />Pedidos</li><li><i data-series="deliveries" />Entregas</li></ul>
    </div>
    <div className="overview-chart" role="img" aria-label={`${orders} pedidos e ${deliveries} entregas`}>
      <span className="overview-grid-line" /><span className="overview-grid-line" /><span className="overview-grid-line" />
      <div className="overview-chart-column"><strong>{orders}</strong><span className="overview-bar overview-bar-orders" style={{ height: `${Math.max(8, orders / max * 100)}%` }} /><small>Pedidos</small></div>
      <div className="overview-chart-column"><strong>{deliveries}</strong><span className="overview-bar overview-bar-deliveries" style={{ height: `${Math.max(8, deliveries / max * 100)}%` }} /><small>Entregas</small></div>
    </div>
  </section>;
}

function TripSituation({ trips }: { readonly trips: OperationalIndicators["trips"] }) {
  const total = Math.max(trips.total, 1);
  const scheduledEnd = trips.scheduled / total * 360;
  const routeEnd = scheduledEnd + trips.inRoute / total * 360;
  const style = { "--scheduled-end": `${scheduledEnd}deg`, "--route-end": `${routeEnd}deg` } as CSSProperties;
  return <section className="overview-panel overview-trips" aria-labelledby="overview-trips-title">
    <div className="overview-panel-heading"><div><h2 id="overview-trips-title">Situação das viagens</h2><p>Distribuição desde o início</p></div></div>
    <div className="overview-trip-content">
      <div className="overview-donut" style={style} aria-hidden="true"><span><strong>{trips.total}</strong>{trips.total === 1 ? "viagem" : "viagens"}</span></div>
      <ul><li><i data-trip="route" /><span>Em rota</span><strong>{trips.inRoute}</strong></li><li><i data-trip="scheduled" /><span>Programadas</span><strong>{trips.scheduled}</strong></li><li><i data-trip="finished" /><span>Concluídas</span><strong>{trips.finished}</strong></li></ul>
    </div>
  </section>;
}

type DashboardSnapshot = ReturnType<typeof useDashboardTotals>;

function DriverOverview() {
  return <div className="entity-page overview-page"><header className="entity-header overview-hero"><div><p className="overview-eyebrow">Sua operação</p><h1>Visão geral</h1><p className="entity-lede">Suas viagens e o que falta entregar.</p></div></header><section className="dash-block"><div className="dash-block-head"><h2>Minhas viagens</h2></div><DriverTrips /></section></div>;
}

function OperationalSummary({ data, totals, readsPersonalData }: { readonly data: OperationalIndicators; readonly totals: DashboardSnapshot["totals"]; readonly readsPersonalData: boolean }) {
  return <>
    <div className="overview-kpis">
      <Counter label="Pedidos" value={totals.orders} to="/orders" icon="orders" description="registros persistidos" />
      <Counter label="Entregas" value={data.deliveries.total} to="/deliveries" icon="truck" description="desde o início" />
      <Counter label="Viagens em rota" value={data.trips.inRoute} to="/trips?status=IN_ROUTE" icon="planning" description="em andamento agora" />
      <Counter label="Caminhões disponíveis" value={data.fleet.available} to="/trucks?tab=availability" icon="truck" description="prontos para alocação" />
      {readsPersonalData ? <Counter label="Motoristas" value={totals.drivers} to="/contacts?tab=drivers" icon="users" description="cadastrados no sistema" /> : null}
    </div>
    <div className="overview-analytics"><ComparisonChart orders={totals.orders ?? 0} deliveries={data.deliveries.total} /><TripSituation trips={data.trips} /></div>
  </>;
}

function LimitedSummary({ user, totals }: { readonly user: Parameters<typeof hasPermission>[0]; readonly totals: DashboardSnapshot["totals"] }) {
  return <div className="kpi-grid">
    {hasPermission(user, "loadx.trucks.read") ? <Counter label="Caminhões" value={totals.trucks} to="/trucks" icon="truck" description="cadastrados no sistema" /> : null}
    {hasPermission(user, "loadx.products.read") ? <Counter label="Produtos" value={totals.products} to="/products" icon="package" description="itens no catálogo" /> : null}
    {hasPermission(user, "loadx.orders.read") ? <Counter label="Pedidos" value={totals.orders} to="/orders" icon="orders" description="registros persistidos" /> : null}
  </div>;
}

function RecentOrdersPanel({ recentOrders, unavailable, customerNames }: Pick<DashboardSnapshot, "recentOrders" | "unavailable"> & { readonly customerNames: ReadonlyMap<string, string> }) {
  const emptyMessage = unavailable.includes("orders") ? "Não foi possível consultar os pedidos recentes." : "Nenhum pedido cadastrado ainda.";
  return <section className="overview-panel overview-events"><div className="overview-panel-heading"><div><h2>Últimos acontecimentos</h2><p>Pedidos atualizados recentemente</p></div><Link className="btn-link" to="/orders">Ver todos <Icon name="arrow-right" size={14} /></Link></div>
    {recentOrders.length === 0 ? <p className="entity-state">{emptyMessage}</p> : <ul>{recentOrders.map((order) => <li key={order.id}><span className={`overview-event-dot overview-event-${statusTone(order.status)}`} /><time dateTime={order.createdAt}>{dateFormatter.format(new Date(order.createdAt))}</time><div><Link to={`/orders?order=${order.id}`} aria-label={`Abrir pedido ${order.id}`}><strong>{customerNames.get(order.customerId) ?? `Pedido ${order.id.slice(0, 8)}`}</strong></Link><small>{order.itemCount} {order.itemCount === 1 ? "linha" : "linhas"} · prioridade {priorityLabel(order.priority)}</small></div><StatusPill tone={statusTone(order.status)}>{STATUS_LABELS[order.status]}</StatusPill></li>)}</ul>}
  </section>;
}

function RecentProductsPanel({ recentProducts }: Pick<DashboardSnapshot, "recentProducts">) {
  return <section className="overview-panel overview-products"><div className="overview-panel-heading"><div><h2>Cargas disponíveis</h2><p>Produtos ativos mais recentes</p></div><Link className="btn-link" to="/products">Ver todas <Icon name="arrow-right" size={14} /></Link></div>
    {recentProducts.length === 0 ? <p className="entity-state">Nenhum produto disponível para exibir.</p> : <div className="overview-product-grid">{recentProducts.map((product) => <Link to="/products" className="overview-product-card" key={product.id}><span className="overview-product-state"><i />{product.active ? "Ativo" : "Arquivado"}</span><div><strong title={product.code}>{product.code.length > 16 ? `${product.code.slice(0, 12)}…` : product.code}</strong><b>{numberFormatter.format(product.weightKg)} kg</b></div><p>{product.name}</p><dl><div><dt>Largura</dt><dd>{numberFormatter.format(product.widthCm)} cm</dd></div><div><dt>Altura</dt><dd>{numberFormatter.format(product.heightCm)} cm</dd></div><div><dt>Comprimento</dt><dd>{numberFormatter.format(product.lengthCm)} cm</dd></div></dl></Link>)}</div>}
  </section>;
}

function DashboardLowerPanels({ user, status, recentOrders, recentProducts, unavailable, customerNames }: Pick<DashboardSnapshot, "status" | "recentOrders" | "recentProducts" | "unavailable"> & { readonly user: Parameters<typeof hasPermission>[0]; readonly customerNames: ReadonlyMap<string, string> }) {
  if (status === "loading" || !hasPermission(user, "loadx.orders.read")) return null;
  return <div className="overview-lower-grid">
    <RecentOrdersPanel recentOrders={recentOrders} unavailable={unavailable} customerNames={customerNames} />
    {hasPermission(user, "loadx.products.read") ? <RecentProductsPanel recentProducts={recentProducts} /> : null}
  </div>;
}

export function DashboardPage() {
  const { user } = useAuth();
  const { status, totals, recentOrders, recentProducts, unavailable, reload } = useDashboardTotals(user);
  const readsPersonalData = hasPermission(user, "loadx.customers.read");
  const { items: customers } = useResourceList(listHistoricalCustomers, readsPersonalData);
  const canSeeOperation = user?.role === "ADMIN" || user?.role === "LOGISTICS_MANAGER";
  const operational = useOperationalSnapshot(canSeeOperation);
  const customerNames = useMemo(() => new Map((readsPersonalData ? customers : []).map((customer) => [customer.id, customer.name])), [customers, readsPersonalData]);
  const canPlan = hasPermission(user, "loadx.planning.create");
  const firstName = user?.name.trim().split(/\s+/)[0] ?? "";

  if (user?.role === "DRIVER") {
    return <DriverOverview />;
  }

  return <div className="entity-page overview-page">
    <header className="entity-header overview-hero">
      <div><p className="overview-eyebrow">Bem-vindo{firstName ? `, ${firstName}` : ""}</p><h1>Visão geral</h1><p className="entity-lede">Acompanhe a operação logística em tempo real e acesse os principais indicadores.</p></div>
      <div className="overview-hero-actions">{operational.data ? <span className="overview-live"><i />Dados atualizados</span> : null}{canPlan ? <Link className="btn-primary" to="/planning?tab=new"><Icon name="plus" size={18} />Planejar carga</Link> : null}</div>
    </header>

    {status === "loading" && !operational.data ? <p className="entity-state"><span className="spinner" aria-hidden="true" /><span>Carregando painel…</span></p> : null}
    {canSeeOperation && operational.failed ? <div className="dashboard-partial"><AlertBanner>Não foi possível atualizar os indicadores operacionais. Os demais dados continuam disponíveis.</AlertBanner><button className="btn-secondary" onClick={operational.retry} type="button">Tentar novamente</button></div> : null}

    {canSeeOperation && operational.data ? <OperationalSummary data={operational.data} totals={totals} readsPersonalData={readsPersonalData} /> : null}

    {!canSeeOperation && status !== "loading" ? <LimitedSummary user={user} totals={totals} /> : null}
    {unavailable.length > 0 ? <div className="dashboard-partial"><p className="entity-form-help">Alguns números não puderam ser carregados e aparecem como “—”. O restante do painel continua válido.</p><button className="btn-secondary" onClick={reload} type="button">Tentar novamente o resumo</button></div> : null}

    <DashboardLowerPanels user={user} status={status} recentOrders={recentOrders} recentProducts={recentProducts} unavailable={unavailable} customerNames={customerNames} />
  </div>;
}
