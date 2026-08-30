import { api } from "../../../services/api";
import { ApiError, isApiErrorResponse } from "../../../types/api";

/**
 * Download dos PDFs gerados pelo backend.
 *
 * `GET /reports/load-plans/{id}` e `GET /reports/trips/{id}` devolvem
 * `application/pdf`. Ambos são lidos por `ADMIN` e `LOGISTICS_MANAGER`; o de
 * viagem ainda barra viagem que não é do usuário.
 */

/**
 * `Blob.text()` não existe em todo lugar — o jsdom da suíte de testes é um
 * deles —, então o `FileReader` entra como alternativa. Sem isso o corpo do erro
 * ficava ilegível e todo 404 virava "erro inesperado".
 */
function blobText(blob: Blob): Promise<string> {
  if (typeof blob.text === "function") return blob.text();

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error("Falha ao ler o corpo do erro."));
    reader.readAsText(blob);
  });
}

async function apiErrorFromBlob(body: unknown, status: number): Promise<ApiError> {
  if (body instanceof Blob) {
    try {
      const parsed: unknown = JSON.parse(await blobText(body));
      if (isApiErrorResponse(parsed)) {
        return new ApiError(parsed.code, parsed.message, parsed.details);
      }
    } catch {
      // corpo não era JSON: cai no genérico abaixo
    }
  }

  return new ApiError(
    status === 403 ? "AUTH_FORBIDDEN" : "UNKNOWN_ERROR",
    "Não foi possível gerar o relatório.",
  );
}

async function requestPdf(path: string): Promise<Blob> {
  const response = await api.get<Blob>(path, {
    responseType: "blob",
    // Aceitar qualquer status é proposital: com `responseType: "blob"` o corpo
    // do ERRO também vem como Blob, e o interceptor global converteria a falha
    // antes de nós — o JSON de dentro dele se perderia, e todo 404 viraria
    // "erro inesperado". Aqui a resposta é inspecionada de perto.
    validateStatus: () => true,
  });

  if (response.status >= 200 && response.status < 300) return response.data;

  throw await apiErrorFromBlob(response.data, response.status);
}

export function downloadLoadingReport(loadPlanId: string): Promise<Blob> {
  return requestPdf(`/reports/load-plans/${loadPlanId}`);
}

export function downloadTripReport(tripId: string): Promise<Blob> {
  return requestPdf(`/reports/trips/${tripId}`);
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
