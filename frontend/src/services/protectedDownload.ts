import { api } from "./api";
import { ApiError, isApiErrorResponse } from "../types/api";

async function apiErrorFromBlob(body: unknown, status: number, fallbackMessage: string): Promise<ApiError> {
  if (body instanceof Blob) {
    try {
      const parsed: unknown = JSON.parse(await body.text());
      if (isApiErrorResponse(parsed)) {
        return new ApiError(parsed.code, parsed.message, parsed.details);
      }
    } catch {
      // corpo não era JSON: cai no genérico abaixo
    }
  }

  return new ApiError(
    status === 403 ? "AUTH_FORBIDDEN" : "UNKNOWN_ERROR",
    fallbackMessage,
  );
}

export async function requestProtectedBlob(path: string, fallbackMessage: string): Promise<Blob> {
  const response = await api.get<Blob>(path, {
    responseType: "blob",
    // Aceitar qualquer status é proposital: com `responseType: "blob"` o corpo
    // do ERRO também vem como Blob, e o interceptor global converteria a falha
    // antes de nós — o JSON de dentro dele se perderia, e todo 404 viraria
    // "erro inesperado". Aqui a resposta é inspecionada de perto.
    validateStatus: () => true,
  });

  if (response.status >= 200 && response.status < 300) return response.data;

  throw await apiErrorFromBlob(response.data, response.status, fallbackMessage);
}

