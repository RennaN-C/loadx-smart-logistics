import { describe, expect, it } from "vitest";
import { toPageQuery, toSearchQuery } from "./pagination";

describe("query de coleção OC95", () => {
  it("preserva paginação e normaliza somente search", () => {
    expect(toPageQuery()).toEqual({ page: 1, page_size: 20, sort_order: "desc" });
    expect(toPageQuery({ page: 3, pageSize: 2, sortOrder: "asc" })).toEqual({ page: 3, page_size: 2, sort_order: "asc" });
    expect(toSearchQuery({ search: "  São %_\\  " })).toEqual({ search: "São %_\\" });
    expect(toSearchQuery({ search: " \t " })).toEqual({});
    expect(toSearchQuery()).toEqual({});
  });
});
