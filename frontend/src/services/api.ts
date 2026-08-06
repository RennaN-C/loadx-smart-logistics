import axios from "axios";

import { isApiErrorResponse, type ApiErrorResponse } from "../types/api";
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

export function toApiErrorResponse(error: unknown): ApiErrorResponse {
  if (axios.isAxiosError(error)) {
    if (isApiErrorResponse(error.response?.data)) {
      return error.response.data;
    }

    if (!error.response) {
      return {
        code: "NETWORK_ERROR",
        message: "Não foi possível conectar ao servidor.",
        details: [],
      };
    }
  }

  return {
    code: "UNKNOWN_ERROR",
    message: "Ocorreu um erro inesperado.",
    details: [],
  };
}

let sessionInvalidatedHandler: ((code: string) => void) | null = null;

export function setSessionInvalidatedHandler(handler: ((code: string) => void) | null): void {
  sessionInvalidatedHandler = handler;
}

const SESSION_INVALIDATING_CODES = new Set(["AUTH_INVALID_TOKEN", "AUTH_USER_INACTIVE"]);

export function notifyIfSessionInvalidated(apiError: ApiErrorResponse): void {
  if (SESSION_INVALIDATING_CODES.has(apiError.code)) {
    sessionInvalidatedHandler?.(apiError.code);
  }
}

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const apiError = toApiErrorResponse(error);
    notifyIfSessionInvalidated(apiError);
    return Promise.reject(apiError);
  },
);
