import axios from "axios";

import { ApiError, isApiErrorResponse } from "../types/api";
import { getToken } from "./tokenStorage";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1",
});

api.interceptors.request.use((config) => {
  const token = getToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
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
    sessionInvalidatedHandler?.(apiError.code);
  }
}

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const apiError = toApiError(error);
    notifyIfSessionInvalidated(apiError);
    return Promise.reject(apiError);
  },
);
