import { ImportAction } from "../../registration-imports/components/ImportAction";
import { useCallback, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { MAX_SEARCH_LENGTH, type ListParams } from "../../../services/pagination";
import { Pagination } from "../../../components/Pagination";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics, hasPermission } from "../../auth/permissions";
import { ProductCard } from "../components/ProductCard";
import { ProductForm } from "../components/ProductForm";
import { mapProductErrorToMessage } from "../components/productsErrorMessages";
import { useRegistryList } from "../../../hooks/useRegistryList";
import { ArchiveFilter } from "../../../components/ArchiveFilter";

import { listProducts } from "../api/productsApi";
import type { Product } from "../types";
import "./ProductListPage.css";
import { Icon } from "../../../components/Icon";
import "../../../components/RegistryTable.css";

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

  const canManage = canManageLogistics(user, "products");
  const isFormOpen = isCreating || editingProduct !== null;

  function closeForm() {
    setIsCreating(false);
    setEditingProduct(null);
  }

  async function handleSaved() {
    closeForm();
    await refetch();
  }

  const unfilteredEmpty = search.trim() === "" && restrictionFilter === "all" && archiveStatus === "active" && total === 0;
  return (
    <div className="entity-page products-page">
      <header className="entity-header">
        <div>
          <p className="registry-eyebrow">Cadastros</p><h1>Produtos</h1>
          <p className="entity-lede">Centralize o catálogo de produtos e embalagens usados no transporte.</p>
        </div>
        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            <Icon name="plus" size={16} />
            Novo produto
          </button>
        ) : null}
      </header>

      <div className="entity-toolbar registry-filterbar product-filterbar">
        <label className="registry-filter-field registry-filter-search"><span>Busca</span><input
          type="search"
          aria-label="Buscar por código ou nome"
          placeholder="Buscar código ou produto…"
          value={search}
          onChange={(event) => { goToPage(1); setSearch(event.target.value); }}
          maxLength={MAX_SEARCH_LENGTH}
        /></label>
        <label className="registry-filter-field"><span>Restrições</span><select
          aria-label="Filtrar por restrição"
          value={restrictionFilter}
          onChange={(event) => { goToPage(1); setRestrictionFilter(event.target.value as RestrictionFilter); }}
        >
          <option value="all">Todas as restrições</option>
          <option value="restricted">Com restrição</option>
          <option value="free">Sem restrição</option>
        </select></label>
        <label className="registry-filter-field"><span>Situação</span><ArchiveFilter value={archiveStatus} onChange={setArchiveStatus} /></label>
        <div className="registry-import-action"><ImportAction enabled={hasPermission(user, "loadx.imports.manage")} entity="products" onImported={refetch} /></div>
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

      <ProductEmptyState show={status === "success" && products.length === 0} unfiltered={unfilteredEmpty} />

      {products.length > 0 ? (
        <div className="registry-table-wrap">
          <table className="registry-table product-table">
            <caption className="sr-only">Produtos cadastrados</caption>
            <thead><tr><th scope="col">Código</th><th scope="col">Produto</th><th scope="col">Dimensões</th><th scope="col">Peso</th><th scope="col">Restrições</th><th scope="col">Situação</th><th scope="col">Ações</th></tr></thead>
            <tbody>{products.map((product) => <ProductCard key={product.id} product={product} canManage={canManage} onEdit={setEditingProduct} onChanged={refetch} />)}</tbody>
          </table>
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

function ProductEmptyState({ show, unfiltered }: { readonly show: boolean; readonly unfiltered: boolean }) {
  if (!show) return null;
  return <p className="entity-state">{unfiltered ? "Nenhum produto cadastrado ainda." : "Nenhum produto encontrado com esses filtros."}</p>;
}
