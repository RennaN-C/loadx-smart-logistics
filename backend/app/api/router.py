from fastapi import APIRouter

from app.modules.trucks.router import router as trucks_router

api_router = APIRouter()
api_router.include_router(trucks_router)
