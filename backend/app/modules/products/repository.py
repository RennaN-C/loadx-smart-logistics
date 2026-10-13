import uuid
from collections.abc import Sequence

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.products.models import Product
from app.modules.products.schemas import ProductRestriction
from app.shared.search import search_pattern


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        pagination: PaginationParams,
        *,
        active: bool | None = None,
        search: str | None = None,
        restriction: ProductRestriction | None = None,
    ) -> PageResult[Product]:
        direction = asc if pagination.sort_order == "asc" else desc
        filters = [] if active is None else [Product.active.is_(active)]
        pattern = search_pattern(search)
        if pattern is not None:
            filters.append(
                or_(
                    Product.code.ilike(pattern, escape="\\"),
                    Product.name.ilike(pattern, escape="\\"),
                )
            )
        if restriction == "restricted":
            filters.append(
                or_(
                    Product.fragile.is_(True),
                    Product.stackable.is_(False),
                    Product.rotation_allowed.is_(False),
                )
            )
        elif restriction == "free":
            filters.extend(
                (
                    Product.fragile.is_(False),
                    Product.stackable.is_(True),
                    Product.rotation_allowed.is_(True),
                )
            )
        total = (
            self.db.scalar(select(func.count()).select_from(Product).where(*filters))
            or 0
        )
        statement = (
            select(Product)
            .where(*filters)
            .order_by(direction(Product.created_at), direction(Product.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return PageResult.create(
            self.db.scalars(statement).all(),
            pagination,
            total,
        )

    def get(self, product_id: uuid.UUID) -> Product | None:
        return self.db.get(Product, product_id)

    def get_many(
        self,
        product_ids: Sequence[uuid.UUID],
        *,
        for_update: bool = False,
    ) -> Sequence[Product]:
        unique_ids = tuple(sorted(set(product_ids), key=lambda value: value.int))
        if not unique_ids:
            return ()
        statement = (
            select(Product).where(Product.id.in_(unique_ids)).order_by(Product.id.asc())
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.db.scalars(statement).all()

    def get_for_update(self, product_id: uuid.UUID) -> Product | None:
        statement = (
            select(Product)
            .where(Product.id == product_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(statement)

    def existing_registration_keys(
        self, keys: dict[str, set[str]]
    ) -> dict[str, set[str]]:
        return {
            field: set(
                self.db.scalars(
                    select(getattr(Product, field)).where(
                        getattr(Product, field).in_(keys.get(field, set()))
                    )
                )
            )
            for field in ("code",)
        }

    def get_by_code(self, code: str) -> Product | None:
        statement = select(Product).where(Product.code == code)
        return self.db.scalar(statement)

    def add(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        self.db.refresh(product)
        return product

    def update(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        self.db.refresh(product)
        return product
