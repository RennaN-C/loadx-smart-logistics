"""Read-only business metrics; authorization and definitions precede aggregation."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PaginationParams
from app.modules.access_profiles.catalog import has_permission
from app.modules.assistant.capabilities import CAPABILITIES, permitted
from app.modules.assistant.schemas import CustomerChoice, Source, ToolArguments
from app.modules.company_profile.service import CompanyProfileService
from app.modules.customers.service import CustomerNotFoundError, CustomerService
from app.modules.drivers.service import DriverService
from app.modules.orders.service import OrderService
from app.modules.products.service import ProductService
from app.modules.reports.assistant_repository import AssistantMetricsRepository
from app.modules.reports.management_service import ManagementFilters, validate_window
from app.modules.trucks.operational_status_service import TruckOperationalStatusService
from app.modules.trucks.service import TruckService
from app.modules.users.models import User

GET_COMPANY_SUMMARY = "get_company_summary"
GET_CUSTOMER_ORDER_METRICS = "get_customer_order_metrics"
GET_DELIVERY_METRICS = "get_delivery_metrics"
GET_FLEET_UTILIZATION = "get_fleet_utilization"
GET_FLEET_AVAILABILITY = "get_fleet_availability"
GET_CANCELED_DISTRIBUTIONS = "get_canceled_distributions"
GET_FINANCIAL_IMPACT = "get_financial_impact"
GET_REGISTERED_PRODUCTS = "get_registered_products"
GET_REGISTERED_TRUCKS = "get_registered_trucks"

REPORTS_READ_PERMISSION = "loadx.reports.read"

TOOL_PERMISSIONS = {
    "get_usage_guidance": (),
    "get_registered_customers": ("loadx.customers.read",),
    "get_registered_drivers": ("loadx.drivers.read",),
    "get_registered_orders": ("loadx.orders.read",),
    GET_REGISTERED_PRODUCTS: ("loadx.products.read",),
    GET_REGISTERED_TRUCKS: ("loadx.trucks.read",),
    GET_FLEET_AVAILABILITY: ("loadx.trucks.read",),
    GET_COMPANY_SUMMARY: (),
    GET_CUSTOMER_ORDER_METRICS: (
        REPORTS_READ_PERMISSION,
        "loadx.orders.read",
        "loadx.customers.read",
    ),
    GET_DELIVERY_METRICS: (
        REPORTS_READ_PERMISSION,
        "loadx.deliveries.read",
        "loadx.orders.read",
        "loadx.customers.read",
        "loadx.trips.read",
    ),
    GET_FLEET_UTILIZATION: (
        REPORTS_READ_PERMISSION,
        "loadx.trucks.read",
        "loadx.trips.read",
        "loadx.planning.read",
    ),
    GET_CANCELED_DISTRIBUTIONS: (REPORTS_READ_PERMISSION, "loadx.planning.read"),
    GET_FINANCIAL_IMPACT: (),
}


def allowed_tool(user: User, name: str) -> bool:
    if (
        not user.active
        or name not in TOOL_PERMISSIONS
        or user.role not in {"ADMIN", "LOGISTICS_MANAGER", "CHECKER"}
    ):
        return False
    if user.role == "CHECKER" and name not in {
        "get_usage_guidance",
        GET_FLEET_AVAILABILITY,
        GET_REGISTERED_PRODUCTS,
        GET_REGISTERED_TRUCKS,
    }:
        return False
    if name in {GET_COMPANY_SUMMARY, GET_FINANCIAL_IMPACT}:
        return user.role == "ADMIN"
    return all(
        has_permission(user, permission) for permission in TOOL_PERMISSIONS[name]
    )


class AssistantMetricsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AssistantMetricsRepository(db)

    def query(
        self,
        user: User,
        name: str,
        arguments: ToolArguments,
        *,
        selected_customer_id: uuid.UUID | None = None,
    ) -> Source:
        if not allowed_tool(user, name):
            raise ApiError(
                403,
                "AUTH_FORBIDDEN",
                "Esta consulta não está disponível para seu perfil.",
            )
        if name == "get_usage_guidance":
            cap = next(
                (cap for cap in CAPABILITIES if cap.key == arguments.module), None
            )
            if cap is None:
                raise ApiError(
                    422,
                    "ASSISTANT_MODULE_REQUIRED",
                    "Informe o módulo que deseja conhecer.",
                )
            if not permitted(user, cap):
                raise ApiError(
                    403, "AUTH_FORBIDDEN", "Módulo não autorizado para seu perfil."
                )
            return Source(
                name="Como usar: " + cap.title,
                criteria="Documentação funcional; contrato GET "
                + cap.endpoint
                + "; nenhum cadastro consultado.",
                values={"orientation": cap.guide},
                links=[{"label": "Abrir " + cap.title, "href": cap.route}],
            )
        if name in {
            "get_registered_customers",
            "get_registered_drivers",
            "get_registered_orders",
        }:
            return self._registered_records(name, arguments)
        if name == GET_REGISTERED_PRODUCTS:
            return self._registered_products(arguments.page)
        if name == GET_REGISTERED_TRUCKS:
            return self._registered_trucks(arguments.page)
        if name == GET_FLEET_AVAILABILITY:
            return self._availability(arguments.page)
        end = arguments.end or datetime.now(UTC)
        start = arguments.start or end - timedelta(days=30)
        window = validate_window(ManagementFilters(start=start, end=end))
        customer_id, selection, customer_label = self._customer(
            name, arguments, selected_customer_id
        )
        if selection is not None:
            return selection
        metadata = self._metadata(name)
        if metadata is not None:
            return metadata
        if name == GET_CUSTOMER_ORDER_METRICS:
            values = self.repository.orders(
                window.start, window.end, customer_id, arguments.status
            )
            criteria = "Pedidos criados no período, agrupados pela situação atual; não equivale a expedição. Origem: pedidos."
            label = "Pedidos por situação atual"
        elif name == GET_DELIVERY_METRICS:
            values = self.repository.deliveries(window.start, window.end, customer_id)
            criteria = "Expedidos: pedido distinto em perna não cancelada de viagem iniciada no período; entregues: pedido atualmente totalmente entregue, pela última perna concluída no período. Pernas concluídas são contadas separadamente. Origem: pedidos, viagens e entregas."
            label = "Expedição e entregas"
        elif name == GET_FLEET_UTILIZATION:
            values = self.repository.fleet(window.start, window.end)
            criteria = "Viagens iniciadas/concluídas pelos respectivos timestamps. Caminhões distintos e planos de viagens iniciadas; ocupação média aritmética dos planos, não ganho financeiro. Volumes/peso são snapshots planejados, não comprovantes de entrega. Origem: viagens e planos."
            label = "Utilização operacional da frota"
        elif name == GET_CANCELED_DISTRIBUTIONS:
            return self._canceled(window, arguments.page)
        else:
            raise ApiError(403, "AUTH_FORBIDDEN", "Ferramenta não disponível.")
        return Source(
            name=label,
            period_start=window.start,
            period_end=window.end,
            criteria=criteria,
            values=values,
            filter_label="Cliente filtrado: " + customer_label
            if customer_label
            else None,
        )

    def _registered_records(self, name: str, arguments: ToolArguments) -> Source:
        pagination = PaginationParams(
            page=arguments.page, page_size=10, sort_order="desc"
        )
        if name == "get_registered_customers":
            page = CustomerService(self.db).list_customers(pagination, active=True)
            labels = [item.name[:100] for item in page.items]
            title, route, criterion = (
                "Clientes cadastrados",
                "/contacts",
                "Somente clientes ativos, sem documentos, contatos ou endereços.",
            )
        elif name == "get_registered_drivers":
            page = DriverService(self.db).list_drivers(pagination, active=True)
            labels = [item.name[:100] for item in page.items]
            title, route, criterion = (
                "Motoristas cadastrados",
                "/contacts",
                "Somente motoristas ativos, sem CNH, documentos ou contatos; não indica disponibilidade.",
            )
        else:
            page = OrderService(self.db).list_orders(
                pagination, status=arguments.status
            )
            labels = [
                "Pedido " + str(item.id)[:8] + " · " + item.status
                for item in page.items
            ]
            title, route, criterion = (
                "Pedidos cadastrados",
                "/orders",
                "Filtro de situação: "
                + (arguments.status or "todas")
                + ". Sem dados pessoais do destino.",
            )
        values = {
            "total_records": page.total,
            "page": page.page,
            "total_pages": page.total_pages,
            "page_records": len(page.items),
        }
        values.update({f"item_{index}": label for index, label in enumerate(labels, 1)})
        return Source(
            name=title,
            criteria=criterion
            + " Até dez registros por página, mais recentes primeiro. Origem: service público do módulo.",
            values=values,
            links=[{"label": "Abrir " + title, "href": route}],
        )

    def _registered_products(self, page: int) -> Source:
        """Only catalog data; do not send names or identifiers to the LLM."""
        result = ProductService(self.db).list_products(
            PaginationParams(page=page, page_size=10, sort_order="asc")
        )
        values: dict[str, int | float | str | None] = {
            "total_records": result.total,
            "page": result.page,
            "total_pages": result.total_pages,
            "page_records": len(result.items),
        }
        for index, product in enumerate(result.items, start=1):
            status = "Ativo" if product.active else "Arquivado"
            values[f"item_{index}"] = (
                f"{product.name[:100]} · código {product.code[:40]} · {status}"
            )
        return Source(
            name="Produtos cadastrados",
            criteria=(
                "Listagem paginada dos produtos cadastrados, incluindo arquivados. "
                "Até 10 por página, em ordem de criação; não informa estoque."
            ),
            values=values,
        )

    def _registered_trucks(self, page: int) -> Source:
        """Registration and operational availability are different concepts."""
        result = TruckService(self.db).list_trucks(
            PaginationParams(page=page, page_size=10, sort_order="asc")
        )
        values: dict[str, int | float | str | None] = {
            "total_records": result.total,
            "page": result.page,
            "total_pages": result.total_pages,
            "page_records": len(result.items),
        }
        for index, truck in enumerate(result.items, start=1):
            status = "Ativo" if truck.active else "Arquivado"
            values[f"item_{index}"] = (
                f"{truck.model[:100]} · placa {truck.plate[:16]} · {status}"
            )
        return Source(
            name="Caminhões cadastrados",
            criteria=(
                "Listagem paginada dos caminhões cadastrados, incluindo arquivados. "
                "Até 10 por página; disponibilidade operacional deve ser consultada separadamente."
            ),
            values=values,
        )

    def _availability(self, page: int) -> Source:
        result = TruckOperationalStatusService(self.db).list_statuses(
            PaginationParams(page=page, page_size=20, sort_order="desc")
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
                "page_archived_count": sum(not item.active for item in result.items),
                "page_unavailable_count": len(unavailable),
                "unavailable_vehicles": ", ".join(unavailable) or "Nenhum nesta página",
            },
        )

    def _metadata(self, name: str) -> Source | None:
        if name == GET_COMPANY_SUMMARY:
            company = CompanyProfileService(self.db).get()
            return Source(
                name="Empresa operadora",
                criteria="Cadastro institucional monoempresa; separado dos clientes destinatários.",
                values={"company": company.display_name if company else None},
            )
        if name == GET_FINANCIAL_IMPACT:
            return Source(
                name="Impacto financeiro",
                criteria="Não há receita, custo total de viagem ou baseline comparável aprovado. Sem cálculos financeiros nem percentual de melhoria.",
                values={
                    "result": "insufficient_data",
                    "required_data": "Receitas, custos comparáveis e linha de base validada maior que zero.",
                },
            )
        return None

    def _customer(
        self,
        name: str,
        arguments: ToolArguments,
        selected_customer_id: uuid.UUID | None,
    ) -> tuple[uuid.UUID | None, Source | None, str | None]:
        customer_id = None
        if (
            name in {GET_CUSTOMER_ORDER_METRICS, GET_DELIVERY_METRICS}
            and selected_customer_id is not None
        ):
            try:
                customer = CustomerService(self.db).get_customer(selected_customer_id)
            except CustomerNotFoundError:
                raise ApiError(
                    404, "CUSTOMER_NOT_FOUND", "Cliente não encontrado."
                ) from None
            return customer.id, None, _customer_label(customer)
        if arguments.customer and name in {
            GET_CUSTOMER_ORDER_METRICS,
            GET_DELIVERY_METRICS,
        }:
            customers = self.repository.customers(arguments.customer)
            if len(customers) != 1:
                return (
                    None,
                    Source(
                        name="Seleção de cliente",
                        criteria="Selecione um cliente autorizado nas opções para consultar sem ambiguidade."
                        if customers
                        else "Nenhum cliente corresponde ao nome informado. Revise o nome ou consulte os cadastros autorizados.",
                        choices=[
                            CustomerChoice(
                                reference=customer.id,
                                label=_customer_label(customer),
                            )
                            for customer in customers
                        ],
                        values={
                            "result": "ambiguous_customer"
                            if customers
                            else "customer_not_found",
                            "bounded_matches": len(customers),
                        },
                    ),
                    None,
                )
            customer_id = customers[0].id
        return customer_id, None, _customer_label(customers[0]) if customer_id else None

    def _canceled(self, window: ManagementFilters, page: int) -> Source:
        values = self.repository.canceled(window.start, window.end)
        items = self.repository.canceled_items(window.start, window.end, page)
        return Source(
            name="Distribuições canceladas",
            period_start=window.start,
            period_end=window.end,
            criteria="Distribuições atualmente canceladas, criadas no período (não data do cancelamento). Origem: distribuições persistidas; página de até dez registros, ordenada por criação e identificador.",
            values={
                **values,
                "page": page,
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


def _customer_label(customer) -> str:
    return f"{customer.name.strip()} — {customer.city}/{customer.state} · documento …{customer.document[-4:]}"
