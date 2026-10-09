import { requestProtectedBlob } from "../../../services/protectedDownload";

/**
 * Download dos PDFs gerados pelo backend.
 *
 * `GET /reports/load-plans/{id}` e `GET /reports/trips/{id}` devolvem
 * `application/pdf`. Os dois são lidos por `ADMIN` e `LOGISTICS_MANAGER`.
 */

export function downloadLoadingReport(loadPlanId: string): Promise<Blob> {
  return requestProtectedBlob(`/reports/load-plans/${loadPlanId}`, "Não foi possível gerar o relatório.");
}

export function downloadTripReport(tripId: string): Promise<Blob> {
  return requestProtectedBlob(`/reports/trips/${tripId}`, "Não foi possível gerar o relatório.");
}

/**
 * Entrega o arquivo ao navegador. O link é criado, clicado e removido no ato;
 * a URL do objeto é liberada num tique seguinte porque revogar no mesmo quadro
 * cancela o download em alguns navegadores.
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
