import type { Page } from "../types/api";

/** Envelope paginado do backend, em snake_case (ADR-017). */
export interface PageDto<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ListParams {
  archiveStatus?: "active" | "archived" | "all";
  page?: number;
  pageSize?: number;
  sortOrder?: "asc" | "desc";
}

export interface SearchListParams extends ListParams {
  search?: string;
}

export const MAX_SEARCH_LENGTH = 120;

/** Busca comum da OC95; filtros específicos permanecem nos adapters de cada recurso. */
export function toSearchQuery({ search }: SearchListParams = {}): Record<string, string> {
  const term = search?.trim();
  return term ? { search: term } : {};
}

export const DEFAULT_PAGE_SIZE = 20;

/** Teto do backend (`MAX_PAGE_SIZE` em core/pagination.py): pedir mais dá 422. */
export const MAX_PAGE_SIZE = 100;

/** Paginação compartilhada da ADR-017; filtros pertencem à whitelist de cada recurso. */
export function toPageQuery({
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE,
  sortOrder = "desc",
}: ListParams = {}): Record<string, string | number> {
  return { page, page_size: pageSize, sort_order: sortOrder };
}

export function mapPageFromDto<D, T>(dto: PageDto<D>, mapItem: (item: D) => T): Page<T> {
  return {
    items: dto.items.map(mapItem),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
  };
}
