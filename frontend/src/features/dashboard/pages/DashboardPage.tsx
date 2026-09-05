import { Link } from "react-router-dom";

import { StatusPill } from "../../../components/StatusPill";
import { useAuth } from "../../auth/hooks/useAuth";
import { useResourceList } from "../../../hooks/useResourceList";
import { listCustomers } from "../../customers/api/customersApi";
import { STATUS_LABELS, priorityLabel, statusTone } from "../../orders/components/orderLabels";
import { useDashboardTotals } from "../hooks/useDashboardTotals";
import "./DashboardPage.css";
import { DriverTrips } from "../components/DriverTrips";

const dateFormatter = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" });

interface CounterProps {
  readonly label: string;
  readonly value: number | null;
  readonly to: string;
}

function Counter({ label, value, to }: CounterProps) {
  return (
    <Link className="kpi" to={to}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value ?? "—"}</span>
    </Link>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const { status, totals, recentOrders, unavailable } = useDashboardTotals(user?.role);
  const { items: customers } = useResourceList(listCustomers);

  const customerNames = new Map(customers.map((customer) => [customer.id, customer.name]));
  const readsPersonalData = user?.role === "ADMIN" || user?.role === "LOGISTICS_MANAGER";
  const canPlan = user?.role === "LOGISTICS_MANAGER";

  /**
   * O motorista não lê caminhões, produtos, pedidos nem clientes: TODOS os
   * contadores deste painel respondem 403 para ele. O painel de cadastros
   * simplesmente não é para esse perfil — o que interessa a ele são as viagens
   * que recebeu, e é isso que a tela mostra.
   */
  if (user?.role === "DRIVER") {
    return (
      <div className="entity-page">
        <header className="entity-header">
          <div>
            <h1>Olá, {user.name.split(" ")[0]}</h1>
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
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Olá, {user?.name.split(" ")[0]}</h1>
          <p className="entity-lede">O que já está cadastrado e o que entrou por último.</p>
        </div>
        {canPlan ? (
          <Link className="btn-primary" to="/planning">
            Planejar carga
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
            <Counter label="CAMINHÕES" value={totals.trucks} to="/trucks" />
            <Counter label="PRODUTOS" value={totals.products} to="/products" />
            {readsPersonalData ? (
              <>
                <Counter label="CLIENTES" value={totals.customers} to="/contacts" />
                <Counter label="MOTORISTAS" value={totals.drivers} to="/contacts" />
              </>
            ) : null}
            <Counter label="PEDIDOS" value={totals.orders} to="/orders" />
          </div>

          {unavailable.length > 0 ? (
            <p className="entity-form-help">
              Alguns números não puderam ser carregados e aparecem como “—”. O restante do painel
              continua válido.
            </p>
          ) : null}

          <section className="dash-block">
            <div className="dash-block-head">
              <h2>Pedidos mais recentes</h2>
              <Link className="btn-link" to="/orders">
                Ver todos
              </Link>
            </div>

            {recentOrders.length === 0 ? (
              <p className="entity-state">Nenhum pedido cadastrado ainda.</p>
            ) : (
              <ul className="dash-orders">
                {recentOrders.map((order) => (
                  <li key={order.id}>
                    <div>
                      <p className="dash-order-customer">
                        {customerNames.get(order.customerId) ?? "Cliente não encontrado"}
                      </p>
                      <p className="dash-order-meta">
                        {dateFormatter.format(new Date(order.createdAt))} · {order.itemCount}{" "}
                        {order.itemCount === 1 ? "item" : "itens"} · {priorityLabel(order.priority)}
                      </p>
                    </div>
                    <StatusPill tone={statusTone(order.status)}>{STATUS_LABELS[order.status]}</StatusPill>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
