from fastapi import APIRouter

from app.core.responses import openapi_error_responses
from app.modules.attachments.router import router as attachments_router
from app.modules.auth.router import router as auth_router
from app.modules.customers.address_router import router as customer_addresses_router
from app.modules.customers.router import router as customers_router
from app.modules.deliveries.evidence_router import router as evidence_router
from app.modules.deliveries.router import router as deliveries_router
from app.modules.drivers.document_router import router as driver_documents_router
from app.modules.drivers.document_router import (
    type_router as driver_document_types_router,
)
from app.modules.drivers.router import router as drivers_router
from app.modules.load_planning.distribution_router import router as distribution_router
from app.modules.load_planning.router import router as load_planning_router
from app.modules.loading.router import router as loading_router
from app.modules.messages.router import router as messages_router
from app.modules.occurrences.router import router as occurrences_router
from app.modules.operational_indicators.router import (
    router as operational_indicators_router,
)
from app.modules.orders.router import router as orders_router
from app.modules.products.router import router as products_router
from app.modules.reports.router import router as reports_router
from app.modules.status_history.router import router as audit_router
from app.modules.trucks.document_router import router as truck_documents_router
from app.modules.trucks.maintenance_router import router as maintenance_router
from app.modules.trucks.router import router as trucks_router
from app.modules.users.router import router as users_router

api_router = APIRouter(responses=openapi_error_responses(500))
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(customers_router)
api_router.include_router(customer_addresses_router)
api_router.include_router(deliveries_router)
api_router.include_router(evidence_router)
api_router.include_router(drivers_router)
api_router.include_router(driver_documents_router)
api_router.include_router(driver_document_types_router)
api_router.include_router(load_planning_router)
api_router.include_router(loading_router)
api_router.include_router(messages_router)
api_router.include_router(occurrences_router)
api_router.include_router(operational_indicators_router)
api_router.include_router(orders_router)
api_router.include_router(products_router)
api_router.include_router(reports_router)
api_router.include_router(trucks_router)
api_router.include_router(maintenance_router)
api_router.include_router(truck_documents_router)
api_router.include_router(users_router)

api_router.include_router(distribution_router)

api_router.include_router(attachments_router)
