import { AlertBanner } from "../../../components/AlertBanner";
import { Avatar } from "../../../components/Avatar";
import { Icon } from "../../../components/Icon";
import { StatusPill } from "../../../components/StatusPill";
import { priorityLabel, STATUS_LABELS, statusTone } from "../../orders/components/orderLabels";
import type { OrderStatus } from "../../orders/types";
import { DistributionBars } from "../components/DistributionBars";
import { useOrderReport } from "../hooks/useOrderReport";
import "./ReportsPage.css";

const dateFormatter = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

/** Verde no que terminou bem, cinza no cancelado, acento no que está em curso. */
function statusToneBar(key: OrderStatus): "accent" | "muted" | "good" {
  if (key === "DELIVERED") return "good";
  if (key === "CANCELED") return "muted";
  return "accent";
}

export function ReportsPage() {
  const { status, report, customerNames, notCounted, reference, reload } = useOrderReport();

  if (status === "loading") {
    return (
      <div className="entity-page">
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Apurando indicadores…</span>
        </p>
      </div>
    );
  }

  if (status === "error" || report === null) {
    return (
      <div className="entity-page">
        <AlertBanner>Não foi possível apurar os indicadores. Tente novamente.</AlertBanner>
        <button type="button" className="btn-secondary" onClick={reload}>
          Recarregar
        </button>
      </div>
    );
  }

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Indicadores</h1>
          <p className="entity-lede">
            Apurado sobre os pedidos em {dateFormatter.format(reference)}.
          </p>
        </div>
        <div className="entity-toolbar">
          <button type="button" className="btn-secondary" onClick={reload}>
            Atualizar
          </button>
        </div>
      </header>

      {notCounted > 0 ? (
        <AlertBanner>
          {notCounted} pedido(s) ficaram fora desta apuração: a tela lê no máximo 1000 por vez.
        </AlertBanner>
      ) : null}

      {report.total === 0 ? (
        <p className="entity-state">
          Ainda não há pedidos para apurar. Cadastre um pedido para os indicadores aparecerem.
        </p>
      ) : (
        <>
          <div className="report-kpis">
            <div className="report-kpi">
              <span className="report-kpi-label">
                <Icon name="orders" size={12} />
                PEDIDOS
              </span>
              <span className="report-kpi-value">{report.total}</span>
            </div>
            <div className="report-kpi">
              <span className="report-kpi-label">
                <Icon name="planning" size={12} />
                EM ABERTO
              </span>
              <span className="report-kpi-value">{report.open}</span>
              <span className="report-kpi-note">Nem entregues, nem cancelados.</span>
            </div>
            <div className="report-kpi">
              <span className="report-kpi-label">
                <Icon name="package" size={12} />
                VOLUMES A CARREGAR
              </span>
              <span className="report-kpi-value">{report.openVolumes}</span>
              <span className="report-kpi-note">Dos pedidos em aberto.</span>
            </div>
            <div className={report.late > 0 ? "report-kpi report-kpi-alert" : "report-kpi"}>
              <span className="report-kpi-label">
                <Icon name="calendar" size={12} />
                ATRASADOS
              </span>
              <span className="report-kpi-value">{report.late}</span>
              <span className="report-kpi-note">Previsão vencida e ainda em aberto.</span>
            </div>
          </div>

          <div className="report-block report-columns">
            <section>
              <div className="report-block-head">
                <h2>
                  <Icon name="orders" size={17} />
                  Por situação
                </h2>
              </div>
              <DistributionBars
                slices={report.byStatus}
                label={(key) => STATUS_LABELS[key]}
                tone={statusToneBar}
              />
            </section>

            <section>
              <div className="report-block-head">
                <h2>
                  <Icon name="priority" size={17} />
                  Por prioridade
                </h2>
              </div>
              <DistributionBars slices={report.byPriority} label={priorityLabel} />
            </section>
          </div>

          {report.lateOrders.length > 0 ? (
            <section className="report-block">
              <div className="report-block-head">
                <h2>
                  <Icon name="calendar" size={17} />
                  Pedidos atrasados
                </h2>
                <p>Do mais antigo para o mais recente.</p>
              </div>
              <div className="report-table-scroll">
                <table className="report-table">
                  <thead>
                    <tr>
                      <th>CLIENTE</th>
                      <th>SITUAÇÃO</th>
                      <th>PRIORIDADE</th>
                      <th>PREVISÃO</th>
                      <th className="report-table-num">VOLUMES</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.lateOrders.map((order) => (
                      <tr key={order.id}>
                        <td>{customerNames.get(order.customerId) ?? "—"}</td>
                        <td>
                          <StatusPill tone={statusTone(order.status)}>
                            {STATUS_LABELS[order.status]}
                          </StatusPill>
                        </td>
                        <td>{priorityLabel(order.priority)}</td>
                        <td className="report-table-late">
                          {order.expectedDeliveryAt
                            ? dateFormatter.format(new Date(order.expectedDeliveryAt))
                            : "—"}
                        </td>
                        <td className="report-table-num">{order.itemCount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {customerNames.size > 0 ? (
            <section className="report-block">
              <div className="report-block-head">
                <h2>
                  <Icon name="users" size={17} />
                  Por cliente
                </h2>
                <p>Ordenado pelo maior volume.</p>
              </div>
              <div className="report-table-scroll">
                <table className="report-table">
                  <thead>
                    <tr>
                      <th>CLIENTE</th>
                      <th className="report-table-num">PEDIDOS</th>
                      <th className="report-table-num">VOLUMES</th>
                      <th className="report-table-num">ATRASADOS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.byCustomer.map((row) => {
                      const nome = customerNames.get(row.customerId) ?? "Cliente não encontrado";
                      return (
                        <tr key={row.customerId}>
                          <td>
                            <span className="report-table-who">
                              <Avatar name={nome} size={28} />
                              <span>{nome}</span>
                            </span>
                          </td>
                          <td className="report-table-num">{row.orders}</td>
                          <td className="report-table-num">{row.volumes}</td>
                          <td
                            className={
                              row.late > 0
                                ? "report-table-num report-table-late"
                                : "report-table-num"
                            }
                          >
                            {row.late > 0 ? row.late : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <p className="entity-form-help report-block">
              O relatório por cliente não aparece para este perfil: conferente não lê dados de
              clientes.
            </p>
          )}
        </>
      )}
    </div>
  );
}
