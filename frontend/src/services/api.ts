import axios from "axios";

import { ApiError, isApiErrorResponse } from "../types/api";
import { clearCsrfToken, getCsrfToken, setCsrfToken } from "./csrfToken";

const CSRF_HEADER_NAME = "X-CSRF-Token";
const UNSAFE_METHODS = new Set(["post", "put", "patch", "delete"]);

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api/v1",
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const csrfToken = getCsrfToken();
  const method = config.method?.toLowerCase();

  if (csrfToken && method && UNSAFE_METHODS.has(method)) {
    config.headers.set(CSRF_HEADER_NAME, csrfToken);
  }

  return config;
});

export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    if (isApiErrorResponse(error.response?.data)) {
      const { code, message, details } = error.response.data;
      return new ApiError(code, message, details);
    }

    if (!error.response) {
      return new ApiError("NETWORK_ERROR", "Não foi possível conectar ao servidor.");
    }
  }

  return new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
}

let sessionInvalidatedHandler: ((code: string) => void) | null = null;

export function setSessionInvalidatedHandler(handler: ((code: string) => void) | null): void {
  sessionInvalidatedHandler = handler;
}

const SESSION_INVALIDATING_CODES = new Set(["AUTH_INVALID_TOKEN", "AUTH_USER_INACTIVE"]);

export function notifyIfSessionInvalidated(apiError: ApiError): void {
  if (SESSION_INVALIDATING_CODES.has(apiError.code)) {
    clearCsrfToken();
    sessionInvalidatedHandler?.(apiError.code);
  }
}

api.interceptors.response.use(
  (response) => {
    const csrfToken = response.headers[CSRF_HEADER_NAME.toLowerCase()];
    if (typeof csrfToken === "string" && csrfToken.length > 0) {
      setCsrfToken(csrfToken);
    }
    return response;
  },
  (error: unknown) => {
    const apiError = toApiError(error);
    notifyIfSessionInvalidated(apiError);
    return Promise.reject(apiError);
  },
);
