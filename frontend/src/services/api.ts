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

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(toApiErrorResponse(error)),
);
