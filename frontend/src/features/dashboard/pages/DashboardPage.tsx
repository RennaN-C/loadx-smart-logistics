import { Link } from "react-router-dom";

import { StatusPill } from "../../../components/StatusPill";
import { Icon, type IconName } from "../../../components/Icon";
import { useAuth } from "../../auth/hooks/useAuth";
import { hasPermission } from "../../auth/permissions";
import type { ListParams } from "../../../services/pagination";
import { useResourceList } from "../../../hooks/useResourceList";
import { listCustomers } from "../../customers/api/customersApi";
import { STATUS_LABELS, priorityLabel, statusTone } from "../../orders/components/orderLabels";
import { useDashboardTotals } from "../hooks/useDashboardTotals";
import "./DashboardPage.css";
import { OperationsDashboardPage } from "../../operations/pages/OperationsDashboardPage";
import { DriverTrips } from "../components/DriverTrips";

const dateFormatter = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" });

interface CounterProps {
  readonly label: string;
  readonly value: number | null;
  readonly to: string;
  readonly icon: IconName;
  readonly description: string;
}

function Counter({ label, value, to, icon, description }: CounterProps) {
  return (
    <Link className="kpi" to={to}>
      <span className="kpi-icon"><Icon name={icon} size={20} /></span>
      <span className="kpi-content"><span className="kpi-label">{label}</span>
      <span className="kpi-value">{value ?? "—"}</span>
      <span className="kpi-description">{description}</span></span>
      <Icon name="arrow-right" size={17} />
    </Link>
  );
}

const listHistoricalCustomers = (params: ListParams) => listCustomers({ ...params, archiveStatus: "all" });

export function DashboardPage() {
  const { user } = useAuth();
  const { status, totals, recentOrders, unavailable, reload } = useDashboardTotals(user);
  const readsPersonalData = hasPermission(user, "loadx.customers.read");
  const { items: customers } = useResourceList(listHistoricalCustomers, readsPersonalData);

  const customerNames = new Map((readsPersonalData ? customers : []).map((customer) => [customer.id, customer.name]));
  const canPlan = hasPermission(user, "loadx.planning.create");
  const firstName = user?.name.trim().split(/\s+/)[0] ?? "";

  /**
   * O motorista não lê caminhões, produtos, pedidos nem clientes: TODOS os
   * contadores deste painel respondem 403 para ele. O painel de cadastros
   * simplesmente não é para esse perfil — o que interessa a ele são as viagens
   * que recebeu, e é isso que a tela mostra.
   */
  if (user?.role === "DRIVER") {
    return (
      <div className="entity-page overview-page">
        <header className="entity-header overview-hero">
          <div>
            <p className="overview-eyebrow">Sua operação</p>
            <h1>Visão geral</h1>
            <p className="entity-lede">Suas viagens e o que falta entregar.</p>
          </div>
        </header>

        <section className="dash-block">
          <div className="dash-block-head">
            <h2>Minhas viagens</h2>
          </div>
          <DriverTrips />
        </section>
      </div>
    );
  }

  return (
    <div className="entity-page overview-page">
      <header className="entity-header overview-hero">
        <div>
          <p className="overview-eyebrow">Bem-vindo{firstName ? `, ${firstName}` : ""}</p>
          <h1>Visão geral</h1>
          <p className="entity-lede">Acompanhe a operação logística e acesse os próximos passos.</p>
        </div>
        {canPlan ? (
          <Link className="btn-primary" to="/planning">
            <Icon name="plus" size={18} /> Planejar carga
          </Link>
        ) : null}
      </header>

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando painel…</span>
        </p>
      ) : (
        <>
          <div className="kpi-grid">
            {!canPlan && hasPermission(user, "loadx.trucks.read") && <Counter label="Caminhões" value={totals.trucks} to="/trucks" icon="truck" description="cadastrados no sistema" />}
            {hasPermission(user, "loadx.products.read") && <Counter label="Produtos" value={totals.products} to="/products" icon="package" description="itens no catálogo" />}
            {readsPersonalData ? (
              <>
                <Counter label="Clientes" value={totals.customers} to="/contacts" icon="users" description="relacionamentos ativos e históricos" />
                {hasPermission(user, "loadx.drivers.read") && <Counter label="Motoristas" value={totals.drivers} to="/contacts?tab=drivers" icon="users" description="profissionais cadastrados" />}
              </>
            ) : null}
            {hasPermission(user, "loadx.orders.read") && <Counter label="Pedidos" value={totals.orders} to="/orders" icon="orders" description="registros persistidos" />}
          </div>

          <AuthorizedOperationalOverview user={user} />

          {unavailable.length > 0 ? (
            <div className="dashboard-partial"><p className="entity-form-help">
              Alguns números não puderam ser carregados e aparecem como “—”. O restante do painel
              continua válido.
            </p><button className="btn-secondary" onClick={reload} type="button">Tentar novamente o resumo</button></div>
          ) : null}

          {hasPermission(user, "loadx.orders.read") && <section className="dash-block dash-activity">
            <div className="dash-block-head">
              <div><p className="overview-eyebrow">Atividade recente</p><h2>Pedidos mais recentes</h2></div>
              <Link className="btn-link" to="/orders">
                Ver todos
              </Link>
            </div>

            {recentOrders.length === 0 ? (
              <p className="entity-state">{unavailable.includes("orders") ? "Não foi possível consultar os pedidos recentes." : "Nenhum pedido cadastrado ainda."}</p>
            ) : (
              <ul className="dash-orders">
                {recentOrders.map((order) => (
                  <li key={order.id}>
                    <div>
                      <p className="dash-order-customer">
                        {customerNames.get(order.customerId) ?? `Pedido ${order.id.slice(0, 8)}`}
                      </p>
                      <p className="dash-order-meta">
                        {dateFormatter.format(new Date(order.createdAt))} · {order.itemCount}{" "}
                        {order.itemCount === 1 ? "linha" : "linhas"} · {priorityLabel(order.priority)}
                      </p>
                    </div>
                    <StatusPill tone={statusTone(order.status)}>{STATUS_LABELS[order.status]}</StatusPill>
                    <Link className="btn-link" to={`/orders?order=${order.id}`}>Abrir pedido</Link>
                  </li>
                ))}
              </ul>
            )}
          </section>}
        </>
      )}
    </div>
  );
}

function AuthorizedOperationalOverview({ user }: { readonly user: ReturnType<typeof useAuth>["user"] }) {
  return <>      {hasPermission(user, "loadx.reports.read") && (user?.role !== "CUSTOM" || hasPermission(user, "loadx.trucks.read")) && <OperationsDashboardPage embedded />}
      {user?.role === "CUSTOM" && hasPermission(user, "loadx.trips.read") ? <section className="dash-block"><h2>Viagens autorizadas</h2><DriverTrips /></section> : null}</>;
}
