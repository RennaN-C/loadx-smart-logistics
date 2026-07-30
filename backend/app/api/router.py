from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.customers.router import router as customers_router
from app.modules.drivers.router import router as drivers_router
from app.modules.orders.router import router as orders_router
from app.modules.products.router import router as products_router
from app.modules.trucks.router import router as trucks_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(customers_router)
api_router.include_router(drivers_router)
api_router.include_router(orders_router)
api_router.include_router(products_router)
api_router.include_router(trucks_router)
api_router.include_router(users_router)
