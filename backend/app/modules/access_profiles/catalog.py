"""Closed standalone policy. No entitlement, tenant or executable client rules."""

from dataclasses import dataclass
from enum import StrEnum


class Permission(StrEnum):
    CUSTOMERS_READ = "loadx.customers.read"
    CUSTOMERS_MANAGE = "loadx.customers.manage"
    PRODUCTS_READ = "loadx.products.read"
    PRODUCTS_MANAGE = "loadx.products.manage"
    TRUCKS_READ = "loadx.trucks.read"
    TRUCKS_MANAGE = "loadx.trucks.manage"
    DRIVERS_READ = "loadx.drivers.read"
    DRIVERS_MANAGE = "loadx.drivers.manage"
    ORDERS_READ = "loadx.orders.read"
    ORDERS_MANAGE = "loadx.orders.manage"
    PLANNING_READ = "loadx.planning.read"
    PLANNING_CREATE = "loadx.planning.create"
    PLANNING_APPROVE = "loadx.planning.approve"
    LOADING_READ = "loadx.loading.read"
    LOADING_CREATE = "loadx.loading.create"
    LOADING_OPERATE = "loadx.loading.operate"
    TRIPS_READ = "loadx.trips.read"
    TRIPS_MANAGE = "loadx.trips.manage"
    DELIVERIES_READ = "loadx.deliveries.read"
    DELIVERIES_MANAGE = "loadx.deliveries.manage"
    OCCURRENCES_READ = "loadx.occurrences.read"
    OCCURRENCES_MANAGE = "loadx.occurrences.manage"
    REPORTS_READ = "loadx.reports.read"
    MESSAGES_MANAGE = "loadx.messages.manage"
    AUDIT_READ = "loadx.audit.read"
    USERS_MANAGE = "loadx.users.manage"
    PROFILES_MANAGE = "loadx.profiles.manage"
    SETTINGS_MANAGE = "loadx.settings.manage"
    INTEGRATIONS_READ = "loadx.integrations.read"
    IMPORTS_MANAGE = "loadx.imports.manage"
    TRIPS_OWN = "loadx.trips.own"


@dataclass(frozen=True)
class PermissionDefinition:
    code: Permission
    module: str
    label: str
    delegable: bool
    classification: str


CATALOG = (
    PermissionDefinition(
        Permission.CUSTOMERS_READ, "customers", "Consultar clientes", True, "delegable"
    ),
    PermissionDefinition(
        Permission.CUSTOMERS_MANAGE,
        "customers",
        "Gerenciar clientes",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.PRODUCTS_READ, "products", "Consultar produtos", True, "delegable"
    ),
    PermissionDefinition(
        Permission.PRODUCTS_MANAGE, "products", "Gerenciar produtos", True, "delegable"
    ),
    PermissionDefinition(
        Permission.TRUCKS_READ,
        "trucks",
        "Consultar caminhões e frota",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.TRUCKS_MANAGE,
        "trucks",
        "Gerenciar caminhões e frota",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.DRIVERS_READ, "drivers", "Consultar motoristas", True, "delegable"
    ),
    PermissionDefinition(
        Permission.DRIVERS_MANAGE, "drivers", "Gerenciar motoristas", True, "delegable"
    ),
    PermissionDefinition(
        Permission.ORDERS_READ, "orders", "Consultar pedidos", True, "delegable"
    ),
    PermissionDefinition(
        Permission.ORDERS_MANAGE, "orders", "Gerenciar pedidos", True, "delegable"
    ),
    PermissionDefinition(
        Permission.PLANNING_READ,
        "planning",
        "Consultar planejamento",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.PLANNING_CREATE, "planning", "Criar planejamento", True, "delegable"
    ),
    PermissionDefinition(
        Permission.PLANNING_APPROVE,
        "planning",
        "Aprovar planejamento",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.LOADING_READ, "loading", "Consultar carregamento", True, "delegable"
    ),
    PermissionDefinition(
        Permission.LOADING_CREATE, "loading", "Criar carregamento", True, "delegable"
    ),
    PermissionDefinition(
        Permission.LOADING_OPERATE,
        "loading",
        "Conferir carregamento",
        True,
        "operational",
    ),
    PermissionDefinition(
        Permission.TRIPS_READ, "trips", "Consultar viagens", True, "delegable"
    ),
    PermissionDefinition(
        Permission.TRIPS_MANAGE, "trips", "Gerenciar viagens", True, "delegable"
    ),
    PermissionDefinition(
        Permission.DELIVERIES_READ,
        "deliveries",
        "Consultar entregas",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.DELIVERIES_MANAGE,
        "deliveries",
        "Gerenciar entregas",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.OCCURRENCES_READ,
        "occurrences",
        "Consultar ocorrências",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.OCCURRENCES_MANAGE,
        "occurrences",
        "Gerenciar ocorrências",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.REPORTS_READ, "reports", "Consultar relatórios", True, "delegable"
    ),
    PermissionDefinition(
        Permission.MESSAGES_MANAGE,
        "messages",
        "Gerenciar comunicação simulada",
        True,
        "delegable",
    ),
    PermissionDefinition(
        Permission.AUDIT_READ,
        "audit",
        "Consultar auditoria administrativa",
        False,
        "reserved",
    ),
    PermissionDefinition(
        Permission.USERS_MANAGE,
        "users",
        "Administrar contas e credenciais",
        False,
        "reserved",
    ),
    PermissionDefinition(
        Permission.PROFILES_MANAGE,
        "profiles",
        "Administrar perfis e permissões",
        False,
        "reserved",
    ),
    PermissionDefinition(
        Permission.SETTINGS_MANAGE,
        "settings",
        "Administrar configurações da empresa",
        False,
        "reserved",
    ),
    PermissionDefinition(
        Permission.INTEGRATIONS_READ,
        "integrations",
        "Consultar saúde das integrações",
        False,
        "reserved",
    ),
    PermissionDefinition(
        Permission.IMPORTS_MANAGE,
        "imports",
        "Importar cadastros",
        False,
        "non_delegable",
    ),
    PermissionDefinition(
        Permission.TRIPS_OWN,
        "trips",
        "Operar viagens e entregas próprias",
        False,
        "identity",
    ),
)
CATALOG_BY_CODE = {item.code: item for item in CATALOG}
SYSTEM_LABELS = {
    "ADMIN": "Administrador",
    "LOGISTICS_MANAGER": "Gestor de logística",
    "CHECKER": "Conferente",
    "DRIVER": "Motorista",
}
_MANAGER = frozenset(
    item.code
    for item in CATALOG
    if item.delegable and item.code != Permission.LOADING_OPERATE
) | {Permission.AUDIT_READ, Permission.IMPORTS_MANAGE}
SYSTEM_PERMISSIONS = {
    "ADMIN": frozenset(
        item.code for item in CATALOG if item.classification != "identity"
    ),
    "LOGISTICS_MANAGER": _MANAGER,
    "CHECKER": frozenset(
        {
            Permission.PRODUCTS_READ,
            Permission.TRUCKS_READ,
            Permission.ORDERS_READ,
            Permission.PLANNING_READ,
            Permission.LOADING_READ,
            Permission.LOADING_OPERATE,
        }
    ),
    "DRIVER": frozenset({Permission.TRIPS_OWN}),
}


def permissions_for(user) -> frozenset[str]:
    if not user.active:
        return frozenset()
    if user.role == "CUSTOM":
        return frozenset(getattr(user, "_effective_permissions", ()))
    return SYSTEM_PERMISSIONS.get(user.role, frozenset())


def has_permission(user, permission: Permission) -> bool:
    return permission in permissions_for(user)
