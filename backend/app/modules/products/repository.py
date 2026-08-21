import uuid
from collections.abc import Sequence

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.products.models import Product


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, pagination: PaginationParams) -> PageResult[Product]:
        direction = asc if pagination.sort_order == "asc" else desc
        total = self.db.scalar(select(func.count()).select_from(Product)) or 0
        statement = (
            select(Product)
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
            statement = statement.with_for_update()
        return self.db.scalars(statement).all()

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
