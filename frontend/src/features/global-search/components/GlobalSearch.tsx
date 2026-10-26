import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Icon } from "../../../components/Icon";
import { useAuth } from "../../auth/hooks/useAuth";
import type { SearchResult } from "../api/searchApi";
import { SearchResultsPanel } from "./SearchResultsPanel";
import { useSearchResults } from "./useSearchResults";
import "./GlobalSearch.css";

export function GlobalSearch() {
  const { user } = useAuth();
  const [term, setTerm] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const { results, status, retry } = useSearchResults(term.trim(), user);
  const input = useRef<HTMLInputElement>(null);
  const id = useId();
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => { setOpen(false); setTerm(""); }, [location.pathname, location.search]);
  useEffect(() => {
    if (open && active >= 0) document.getElementById(`${id}-option-${active}`)?.scrollIntoView?.({ block: "nearest" });
  }, [active, open, id]);
  function clearSearch() { setTerm(""); setActive(-1); setOpen(true); input.current?.focus(); }
  function retrySearch() { retry(); input.current?.focus(); }
  function choose(result: SearchResult) { setOpen(false); setTerm(""); navigate(result.href); }
  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") { event.preventDefault(); setOpen(false); setActive(-1); return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault(); setOpen(true);
      const delta = event.key === "ArrowDown" ? 1 : -1;
      if (results.length) setActive((index) => {
        if (index < 0) return delta === 1 ? 0 : results.length - 1;
        return (index + delta + results.length) % results.length;
      });
    }
    if (event.key === "Enter" && results.length && open) { event.preventDefault(); choose(results[Math.min(Math.max(active, 0), results.length - 1)]); }
  }
  return <div className="global-search" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <label className="sr-only" htmlFor={`${id}-input`}>Busca global</label>
    <div className="global-search-field"><Icon name="search" size={20} />
      <input ref={input} id={`${id}-input`} type="search" role="combobox" autoComplete="off" placeholder="Buscar registros no LoadX…" maxLength={120}
        value={term} aria-expanded={open} aria-controls={`${id}-results`} aria-autocomplete="list"
        aria-activedescendant={open && active >= 0 && active < results.length ? `${id}-option-${active}` : undefined}
        onFocus={() => setOpen(true)} onChange={(event) => { setTerm(event.target.value); setActive(-1); setOpen(true); }} onKeyDown={handleKeyDown} />
      {term && <button type="button" className="global-search-clear" aria-label="Limpar busca" onClick={clearSearch}>Limpar</button>}
    </div>
    {open ? <SearchResultsPanel id={id} results={results} status={status} active={active} onActive={setActive} onChoose={choose} onRetry={retrySearch} /> : null}
  </div>;
}
