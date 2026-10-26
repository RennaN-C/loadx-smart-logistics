import { useSearchParams } from "react-router-dom";

/** Compartilha o filtro OC95 com links da busca global e navegação do navegador. */
export function useUrlSearch() {
  const [params, setParams] = useSearchParams();
  const search = params.get("search") ?? "";
  function setSearch(value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set("search", value); else next.delete("search");
    setParams(next, { replace: true });
  }
  return [search, setSearch] as const;
}
