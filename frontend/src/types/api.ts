export interface ApiErrorResponse {
  code: string;
  message: string;
  details: unknown[];
}

export interface Page<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate.code === "string" &&
    typeof candidate.message === "string" &&
    Array.isArray(candidate.details)
  );
}

export class ApiError extends Error {
  readonly code: string;
  readonly details: readonly unknown[];
  /**
   * Status HTTP, quando houve resposta. Ausente em falha de rede.
   *
   * O `code` sozinho não basta quando o backend responde FORA do envelope do
   * projeto — um 404 do próprio FastAPI, por exemplo, chega como
   * `UNKNOWN_ERROR` e fica indistinguível de um 500. Guardar o status deixa a
   * feature explicar o caso sem ter que adivinhar.
   */
  readonly status?: number;

  constructor(
    code: string,
    message: string,
    details: readonly unknown[] = [],
    status?: number,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
    this.status = status;
  }
}
