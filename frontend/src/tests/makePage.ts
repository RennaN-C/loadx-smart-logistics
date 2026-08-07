import type { Page } from "../types/api";

/**
 * Monta o envelope paginado da ADR-017 nos testes. Com `totalPages > 1` o total
 * é forçado para além da página, que é o caso usado para exercitar a navegação.
 */
export function makePage<T>(
  items: T[],
  page = 1,
  totalPages = items.length === 0 ? 0 : 1,
): Page<T> {
  return {
    items,
    page,
    pageSize: 20,
    total: totalPages <= 1 ? items.length : 21,
    totalPages,
  };
}
