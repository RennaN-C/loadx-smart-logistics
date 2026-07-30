import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.products.models import Product


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> Sequence[Product]:
        statement = select(Product).order_by(Product.created_at.desc(), Product.code.asc())
        return self.db.scalars(statement).all()

    def get(self, product_id: uuid.UUID) -> Product | None:
        return self.db.get(Product, product_id)

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
