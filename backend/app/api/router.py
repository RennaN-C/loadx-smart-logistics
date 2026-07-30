from fastapi import APIRouter

from app.modules.products.router import router as products_router
from app.modules.trucks.router import router as trucks_router

api_router = APIRouter()
api_router.include_router(products_router)
api_router.include_router(trucks_router)
