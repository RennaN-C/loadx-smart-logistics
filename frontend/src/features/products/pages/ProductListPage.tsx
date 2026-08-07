import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { useAuth } from "../../auth/hooks/useAuth";
import { ProductCard } from "../components/ProductCard";
import { ProductForm } from "../components/ProductForm";
import { mapProductErrorToMessage } from "../components/productsErrorMessages";
import { useResourceList } from "../../../hooks/useResourceList";
import { listProducts } from "../api/productsApi";
import type { Product } from "../types";
import "./ProductListPage.css";

type RestrictionFilter = "all" | "restricted" | "free";

function matchesRestriction(product: Product, filter: RestrictionFilter): boolean {
  const hasRestriction = product.fragile || !product.stackable || !product.rotationAllowed;
  if (filter === "restricted") return hasRestriction;
  if (filter === "free") return !hasRestriction;
  return true;
}

export function ProductListPage() {
  const { user } = useAuth();
  const { status, items: products, error, refetch } = useResourceList(listProducts);
  const [search, setSearch] = useState("");
  const [restrictionFilter, setRestrictionFilter] = useState<RestrictionFilter>("all");
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || editingProduct !== null;

  // GET /products não aceita query param nenhum: busca e filtro são client-side.
  const visibleProducts = useMemo(() => {
    const term = search.trim().toLowerCase();

    return products.filter((product) => {
      const matchesTerm =
        term === "" ||
        product.code.toLowerCase().includes(term) ||
        product.name.toLowerCase().includes(term);

      return matchesTerm && matchesRestriction(product, restrictionFilter);
    });
  }, [products, search, restrictionFilter]);

  function closeForm() {
    setIsCreating(false);
    setEditingProduct(null);
  }

  async function handleSaved() {
    closeForm();
    await refetch();
  }

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Produtos</h1>
          <p className="entity-lede">Volumes disponíveis para compor a carga.</p>
        </div>
        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            + Novo produto
          </button>
        ) : null}
      </header>

      <div className="entity-toolbar">
        <input
          type="search"
          aria-label="Buscar por código ou nome"
          placeholder="Buscar por código ou nome"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select
          aria-label="Filtrar por restrição"
          value={restrictionFilter}
          onChange={(event) => setRestrictionFilter(event.target.value as RestrictionFilter)}
        >
          <option value="all">Todas as restrições</option>
          <option value="restricted">Com restrição</option>
          <option value="free">Sem restrição</option>
        </select>
      </div>

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando produtos…</span>
        </p>
      ) : null}

      {status === "error" && error ? <AlertBanner>{mapProductErrorToMessage(error)}</AlertBanner> : null}

      {status === "success" && visibleProducts.length === 0 ? (
        <p className="entity-state">
          {products.length === 0
            ? "Nenhum produto cadastrado ainda."
            : "Nenhum produto encontrado com esses filtros."}
        </p>
      ) : null}

      {visibleProducts.length > 0 ? (
        <div className="entity-grid">
          {visibleProducts.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              canManage={canManage}
              onEdit={setEditingProduct}
            />
          ))}
        </div>
      ) : null}

      {isFormOpen ? (
        <Modal
          title={editingProduct ? "Editar produto" : "Novo produto"}
          subtitle="Volume unitário"
          onClose={closeForm}
        >
          <ProductForm
            product={editingProduct ?? undefined}
            onSaved={handleSaved}
            onCancel={closeForm}
          />
        </Modal>
      ) : null}
    </div>
  );
}
