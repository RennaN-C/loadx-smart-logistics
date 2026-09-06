interface PaginationProps {
  readonly page: number;
  readonly totalPages: number;
  readonly onChange: (page: number) => void;
  /** Entra no nome acessível: "Paginação de caminhões". */
  readonly label: string;
}

export function Pagination({ page, totalPages, onChange, label }: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <nav className="entity-pagination" aria-label={`Paginação de ${label}`}>
      <button
        type="button"
        className="btn-secondary"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        Anterior
      </button>
      <span>
        Página {page} de {totalPages}
      </span>
      <button
        type="button"
        className="btn-secondary"
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
      >
        Próxima
      </button>
    </nav>
  );
}
