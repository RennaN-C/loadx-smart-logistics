import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate
from app.shared.record_lifecycle import stage_lifecycle_event, validate_reactivation


class ProductNotFoundError(Exception):
    pass


class ProductCodeAlreadyExistsError(Exception):
    pass


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ProductRepository(db)

    def list_products(
        self, pagination: PaginationParams, *, active: bool | None = None
    ) -> PageResult[Product]:
        return self.repository.list(pagination, active=active)

    def get_product(
        self, product_id: uuid.UUID, *, for_update: bool = False
    ) -> Product:
        product = (
            self.repository.get_for_update(product_id)
            if for_update
            else self.repository.get(product_id)
        )
        if product is None:
            raise ProductNotFoundError
        return product

    def get_products(
        self,
        product_ids: Sequence[uuid.UUID],
        *,
        for_update: bool = False,
    ) -> Sequence[Product]:
        return self.repository.get_many(product_ids, for_update=for_update)

    def create_product(self, data: ProductCreate) -> Product:
        return self._persist(lambda: self.stage_create_product(data))

    def stage_create_product(self, data: ProductCreate) -> Product:
        """Stage manual creation rules without committing an outer import."""
        if self.repository.get_by_code(data.code) is not None:
            raise ProductCodeAlreadyExistsError
        return self.repository.add(Product(**data.model_dump()))

    def existing_registration_keys(
        self, keys: dict[str, set[str]]
    ) -> dict[str, set[str]]:
        """Public batched uniqueness boundary, including archived registrations."""
        return self.repository.existing_registration_keys(keys)

    def update_product(
        self,
        product_id: uuid.UUID,
        data: ProductUpdate,
        *,
        changed_by: uuid.UUID | None = None,
    ) -> Product:
        product = self.repository.get_for_update(product_id)
        if product is None:
            raise ProductNotFoundError
        old_active = product.active
        update_data = data.model_dump(exclude_unset=True)

        new_code = update_data.get("code")
        if new_code is not None and new_code != product.code:
            existing_product = self.repository.get_by_code(new_code)
            if existing_product is not None and existing_product.id != product.id:
                raise ProductCodeAlreadyExistsError

        for field_name, value in update_data.items():
            setattr(product, field_name, value)

        def stage_update() -> Product:
            if not old_active and product.active:
                validate_reactivation(ProductCreate, product)
            self.repository.update(product)
            stage_lifecycle_event(
                self.db,
                entity_type="PRODUCT",
                entity_id=product.id,
                old_active=old_active,
                new_active=product.active,
                changed_by=changed_by,
            )
            return product

        return self._persist(stage_update)

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
        except Exception:
            self.db.rollback()
            raise
        return product
