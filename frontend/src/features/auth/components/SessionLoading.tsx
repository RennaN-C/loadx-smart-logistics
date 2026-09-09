export function SessionLoading() {
  return (
    <div className="session-loading" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Carregando…</span>
    </div>
  );
}
