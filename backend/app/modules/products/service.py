import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import get_integrity_constraint_name
from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate


class ProductNotFoundError(Exception):
    pass


class ProductCodeAlreadyExistsError(Exception):
    pass


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ProductRepository(db)

    def list_products(self) -> Sequence[Product]:
        return self.repository.list()

    def get_product(self, product_id: uuid.UUID) -> Product:
        product = self.repository.get(product_id)
        if product is None:
            raise ProductNotFoundError
        return product

    def create_product(self, data: ProductCreate) -> Product:
        if self.repository.get_by_code(data.code) is not None:
            raise ProductCodeAlreadyExistsError

        product = Product(**data.model_dump())
        return self._persist(lambda: self.repository.add(product))

    def update_product(self, product_id: uuid.UUID, data: ProductUpdate) -> Product:
        product = self.get_product(product_id)
        update_data = data.model_dump(exclude_unset=True)

        new_code = update_data.get("code")
        if new_code is not None and new_code != product.code:
            existing_product = self.repository.get_by_code(new_code)
            if existing_product is not None and existing_product.id != product.id:
                raise ProductCodeAlreadyExistsError

        for field_name, value in update_data.items():
            setattr(product, field_name, value)

        return self._persist(lambda: self.repository.update(product))

    def _persist(self, operation: Callable[[], Product]) -> Product:
        try:
            product = operation()
            self.db.commit()
            self.db.refresh(product)
        except IntegrityError as exc:
            self.db.rollback()
            if get_integrity_constraint_name(exc) == "uq_products__code":
                raise ProductCodeAlreadyExistsError from exc
            raise
        return product
