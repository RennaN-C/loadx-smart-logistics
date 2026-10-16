import { ImportAction } from "../../registration-imports/components/ImportAction";
import { useCallback, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { MAX_SEARCH_LENGTH, type ListParams } from "../../../services/pagination";
import { Pagination } from "../../../components/Pagination";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics } from "../../auth/permissions";
import { ProductCard } from "../components/ProductCard";
import { ProductForm } from "../components/ProductForm";
import { mapProductErrorToMessage } from "../components/productsErrorMessages";
import { useRegistryList } from "../../../hooks/useRegistryList";
import { ArchiveFilter } from "../../../components/ArchiveFilter";

import { listProducts } from "../api/productsApi";
import type { Product } from "../types";
import "./ProductListPage.css";
import { Icon } from "../../../components/Icon";

type RestrictionFilter = "all" | "restricted" | "free";

export function ProductListPage() {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [restrictionFilter, setRestrictionFilter] = useState<RestrictionFilter>("all");
  const filteredLoad = useCallback((params: ListParams) => listProducts({
    ...params,
    search,
    restriction: restrictionFilter === "all" ? undefined : restrictionFilter,
  }), [search, restrictionFilter]);
  const {
    status,
    items: products,
    error,
    refetch,
    page,
    total,
    totalPages,
    goToPage,
    archiveStatus,
    setArchiveStatus,
  } = useRegistryList(filteredLoad);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = canManageLogistics(user?.role);
  const isFormOpen = isCreating || editingProduct !== null;

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
            <Icon name="plus" size={16} />
            Novo produto
          </button>
        ) : null}
      </header>

      <div className="entity-toolbar">
        {canManage ? <ImportAction entity="products" onImported={refetch} /> : null}
        <ArchiveFilter value={archiveStatus} onChange={setArchiveStatus} />
        <input
          type="search"
          aria-label="Buscar por código ou nome"
          placeholder="Buscar por código ou nome"
          value={search}
          onChange={(event) => { goToPage(1); setSearch(event.target.value); }}
          maxLength={MAX_SEARCH_LENGTH}
        />
        <select
          aria-label="Filtrar por restrição"
          value={restrictionFilter}
          onChange={(event) => { goToPage(1); setRestrictionFilter(event.target.value as RestrictionFilter); }}
        >
          <option value="all">Todas as restrições</option>
          <option value="restricted">Com restrição</option>
          <option value="free">Sem restrição</option>
        </select>
      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {products.length} de {total} produtos. Busca e filtros consideram toda a lista.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando produtos…</span>
        </p>
      ) : null}

      {status === "error" && error ? <AlertBanner>{mapProductErrorToMessage(error)}</AlertBanner> : null}

      {status === "success" && products.length === 0 ? (
        <p className="entity-state">
          {search.trim() === "" && restrictionFilter === "all" && archiveStatus === "active" && total === 0
            ? "Nenhum produto cadastrado ainda."
            : "Nenhum produto encontrado com esses filtros."}
        </p>
      ) : null}

      {products.length > 0 ? (
        <div className="entity-grid">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              canManage={canManage}
              onEdit={setEditingProduct}
              onChanged={refetch}
            />
          ))}
        </div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="produtos" />
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
