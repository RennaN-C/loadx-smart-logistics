"""Read-only business metrics; authorization and definitions precede aggregation."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PaginationParams
from app.modules.access_profiles.catalog import has_permission
from app.modules.assistant.schemas import Source, ToolArguments
from app.modules.company_profile.service import CompanyProfileService
from app.modules.reports.assistant_repository import AssistantMetricsRepository
from app.modules.reports.management_service import ManagementFilters, validate_window
from app.modules.trucks.operational_status_service import TruckOperationalStatusService
from app.modules.users.models import User

TOOL_PERMISSIONS = {
    "get_fleet_availability": ("loadx.trucks.read",),
    "get_company_summary": (),
    "get_customer_order_metrics": (
        "loadx.reports.read",
        "loadx.orders.read",
        "loadx.customers.read",
    ),
    "get_delivery_metrics": (
        "loadx.reports.read",
        "loadx.deliveries.read",
        "loadx.orders.read",
        "loadx.customers.read",
        "loadx.trips.read",
    ),
    "get_fleet_utilization": (
        "loadx.reports.read",
        "loadx.trucks.read",
        "loadx.trips.read",
        "loadx.planning.read",
    ),
    "get_canceled_distributions": ("loadx.reports.read", "loadx.planning.read"),
    "get_financial_impact": (),
}


def allowed_tool(user: User, name: str) -> bool:
    if (
        not user.active
        or name not in TOOL_PERMISSIONS
        or user.role not in {"ADMIN", "LOGISTICS_MANAGER", "CHECKER"}
    ):
        return False
    if user.role == "CHECKER" and name != "get_fleet_availability":
        return False
    if name in {"get_company_summary", "get_financial_impact"}:
        return user.role == "ADMIN"
    return all(
        has_permission(user, permission) for permission in TOOL_PERMISSIONS[name]
    )


class AssistantMetricsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AssistantMetricsRepository(db)

    def query(self, user: User, name: str, arguments: ToolArguments) -> Source:
        if not allowed_tool(user, name):
            raise ApiError(
                403,
                "AUTH_FORBIDDEN",
                "Esta consulta não está disponível para seu perfil.",
            )
        if name == "get_fleet_availability":
            result = TruckOperationalStatusService(self.db).list_statuses(
                PaginationParams(page=arguments.page, page_size=20, sort_order="desc")
            )
            unavailable = [item.plate for item in result.items if not item.available]
            return Source(
                name="Disponibilidade atual da frota",
                criteria="Snapshot operacional do backend, até 20 cadastros por página. Cadastro ativo e disponibilidade operacional são critérios separados; arquivados não podem operar. Não é um agregado global.",
                values={
                    "page": result.page,
                    "total_pages": result.total_pages,
                    "page_vehicle_count": len(result.items),
                    "page_active_count": sum(item.active for item in result.items),
                    "page_archived_count": sum(
                        not item.active for item in result.items
                    ),
                    "page_unavailable_count": len(unavailable),
                    "unavailable_vehicles": ", ".join(unavailable)
                    or "Nenhum nesta página",
                },
            )
        end = arguments.end or datetime.now(UTC)
        start = arguments.start or end - timedelta(days=30)
        window = validate_window(ManagementFilters(start=start, end=end))
        customer_id = None
        if arguments.customer and name in {
            "get_customer_order_metrics",
            "get_delivery_metrics",
        }:
            customers = self.repository.customers(arguments.customer)
            if len(customers) != 1:
                return Source(
                    name="Seleção de cliente",
                    criteria="Informe o nome completo para identificar um único cliente autorizado.",
                    values={
                        "result": "ambiguous_customer"
                        if customers
                        else "customer_not_found",
                        "bounded_matches": len(customers),
                    },
                )
            customer_id = customers[0].id
        if name == "get_company_summary":
            company = CompanyProfileService(self.db).get()
            return Source(
                name="Empresa operadora",
                criteria="Cadastro institucional monoempresa; separado dos clientes destinatários.",
                values={"company": company.display_name if company else None},
            )
        if name == "get_financial_impact":
            return Source(
                name="Impacto financeiro",
                criteria="Não há receita, custo total de viagem ou baseline comparável aprovado. Sem cálculos financeiros nem percentual de melhoria.",
                values={
                    "result": "insufficient_data",
                    "required_data": "Receitas, custos comparáveis e linha de base validada maior que zero.",
                },
            )
        if name == "get_customer_order_metrics":
            values = self.repository.orders(
                window.start, window.end, customer_id, arguments.status
            )
            criteria = "Pedidos criados no período, agrupados pela situação atual; não equivale a expedição. Origem: pedidos."
            label = "Pedidos por situação atual"
        elif name == "get_delivery_metrics":
            values = self.repository.deliveries(window.start, window.end, customer_id)
            criteria = "Expedidos: pedido distinto em perna não cancelada de viagem iniciada no período; entregues: pedido atualmente totalmente entregue, pela última perna concluída no período. Pernas concluídas são contadas separadamente. Origem: pedidos, viagens e entregas."
            label = "Expedição e entregas"
        elif name == "get_fleet_utilization":
            values = self.repository.fleet(window.start, window.end)
            criteria = "Viagens iniciadas/concluídas pelos respectivos timestamps. Caminhões distintos e planos de viagens iniciadas; ocupação média aritmética dos planos, não ganho financeiro. Volumes/peso são snapshots planejados, não comprovantes de entrega. Origem: viagens e planos."
            label = "Utilização operacional da frota"
        elif name == "get_canceled_distributions":
            values = self.repository.canceled(window.start, window.end)
            items = self.repository.canceled_items(
                window.start, window.end, arguments.page
            )
            return Source(
                name="Distribuições canceladas",
                period_start=window.start,
                period_end=window.end,
                criteria="Distribuições atualmente canceladas, criadas no período (não data do cancelamento). Origem: distribuições persistidas; página de até dez registros, ordenada por criação e identificador.",
                values={
                    **values,
                    "page": arguments.page,
                    "page_records": len(items),
                },
                links=[
                    {
                        "label": "Distribuição criada em "
                        + created_at.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC"),
                        "href": f"/planning/distributions/{identifier}",
                    }
                    for identifier, created_at in items
                ],
            )
        else:
            raise ApiError(403, "AUTH_FORBIDDEN", "Ferramenta não disponível.")
        return Source(
            name=label,
            period_start=window.start,
            period_end=window.end,
            criteria=criteria,
            values=values,
        )
