import type { ArchiveStatus } from "../hooks/useRegistryList";

export function ArchiveFilter({ value, onChange }: {
  readonly value: ArchiveStatus;
  readonly onChange: (value: ArchiveStatus) => void;
}) {
  return <select aria-label="Filtrar cadastros por arquivamento" value={value}
    onChange={(event) => onChange(event.target.value as ArchiveStatus)}>
    <option value="active">Somente ativos</option>
    <option value="archived">Somente arquivados</option>
    <option value="all">Ativos e arquivados</option>
  </select>;
}
