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
  page?: number;
  pageSize?: number;
  sortOrder?: "asc" | "desc";
}

export const DEFAULT_PAGE_SIZE = 20;

/** Teto do backend (`MAX_PAGE_SIZE` em core/pagination.py): pedir mais dá 422. */
export const MAX_PAGE_SIZE = 100;

/**
 * Query params das coleções: `page` 1-based, `page_size` (máx. 100) e
 * `sort_order`. Não existe `sort_by`, busca livre nem filtro server-side — D12
 * mantém isso fora do contrato, então busca e filtro do frontend valem apenas
 * para a página carregada.
 */
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
