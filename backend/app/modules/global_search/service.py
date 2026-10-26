from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.core.pagination import PaginationParams
from app.modules.access_profiles.catalog import Permission, has_permission
from app.modules.customers.service import CustomerService
from app.modules.deliveries.service import TripService
from app.modules.drivers.service import DriverService
from app.modules.global_search.schemas import SearchResponse, SearchResult
from app.modules.orders.service import OrderService
from app.modules.trucks.service import TruckService
from app.modules.users.models import User


class GlobalSearchService:
    """Compose bounded OC95 queries; never query categories the caller cannot read."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, term: str, limit: int, *, current_user: User) -> SearchResponse:
        page = PaginationParams(page=1, page_size=limit, sort_order="desc")
        results: list[SearchResult] = []
        manager = has_permission(current_user, Permission.CUSTOMERS_READ)
        query = urlencode({"search": term})
        if has_permission(current_user, Permission.ORDERS_READ):
            orders = OrderService(self.db).list_orders(
                page, search=term, allow_customer_name_search=manager
            )
            results.extend(
                SearchResult(
                    category="order",
                    id=item.id,
                    title=f"Pedido {item.id}",
                    href=f"/orders?order={item.id}",
                )
                for item in orders.items
            )
        if has_permission(current_user, Permission.TRUCKS_READ):
            trucks = TruckService(self.db).list_trucks(page, active=True, search=term)
            results.extend(
                SearchResult(
                    category="truck",
                    id=item.id,
                    title=f"{item.plate} · {item.model}",
                    href=f"/trucks?{query}",
                )
                for item in trucks.items
            )
        if has_permission(current_user, Permission.CUSTOMERS_READ):
            customers = CustomerService(self.db).list_customers(
                page, active=True, search=term
            )
            results.extend(
                SearchResult(
                    category="customer",
                    id=item.id,
                    title=item.name,
                    href=f"/contacts?tab=customers&{query}",
                )
                for item in customers.items
            )
        if has_permission(current_user, Permission.DRIVERS_READ):
            drivers = DriverService(self.db).list_drivers(
                page, active=True, search=term
            )
            results.extend(
                SearchResult(
                    category="driver",
                    id=item.id,
                    title=item.name,
                    href=f"/contacts?tab=drivers&{query}",
                )
                for item in drivers.items
            )
        if has_permission(current_user, Permission.TRIPS_READ) or has_permission(
            current_user, Permission.TRIPS_OWN
        ):
            trips = TripService(self.db).list_trips(
                page, current_user=current_user, search=term
            )
            results.extend(
                SearchResult(
                    category="trip",
                    id=item.trip.id,
                    title=f"Viagem {item.trip.id}",
                    href=f"/trips/{item.trip.id}",
                )
                for item in trips.items
            )
        return SearchResponse(results=results)
