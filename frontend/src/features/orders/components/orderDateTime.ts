/**
 * Conversão entre o `<input type="datetime-local">` e o contrato da API.
 *
 * O backend REJEITA datetime sem fuso: `normalize_optional_utc` levanta
 * "expected_delivery_at must include timezone". Já o input devolve uma string
 * ingênua ("2026-08-10T14:30"), interpretada no fuso local do navegador.
 * Estas duas funções são a ponte, e existem separadas para poderem ser testadas.
 */

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** ISO em UTC → valor aceito pelo input, no fuso local de quem está olhando. */
export function isoToLocalInput(iso: string | null): string {
  if (!iso) return "";

  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";

  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/** Valor do input (hora local) → ISO em UTC, que sempre carrega o fuso. */
export function localInputToIso(value: string): string | null {
  if (value.trim() === "") return null;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  return date.toISOString();
}
