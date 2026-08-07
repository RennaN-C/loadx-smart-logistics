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

  constructor(code: string, message: string, details: readonly unknown[] = []) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
  }
}
