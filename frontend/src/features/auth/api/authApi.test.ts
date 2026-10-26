import { describe, expect, it, vi } from "vitest";

import { api } from "../../../services/api";
vi.mock("../../../services/api", () => ({ api: { post: vi.fn() } }));

import { login, mapUserFromDto } from "./authApi";

describe("mapUserFromDto", () => {
  it("mapeia created_at para createdAt e preserva os demais campos", () => {
    const result = mapUserFromDto({
      id: "11111111-1111-1111-1111-111111111111",
      name: "Ana Souza",
      email: "ana@example.test",
      role: "LOGISTICS_MANAGER",
      active: true,
      created_at: "2026-08-01T12:00:00Z",
    });

    expect(result).toEqual({
      id: "11111111-1111-1111-1111-111111111111",
      name: "Ana Souza",
      email: "ana@example.test",
      role: "LOGISTICS_MANAGER",
      active: true,
      createdAt: "2026-08-01T12:00:00Z",
    });
  });
});

it("não transforma desafio MFA em usuário autenticado", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { challenge_token: "restricted", purpose: "LOGIN", expires_at: "2026-10-13T12:05:00Z" } });
  await expect(login("conta@example.test", "senha-local-segura")).rejects.toMatchObject({ challenge: { challenge_token: "restricted", purpose: "LOGIN" } });
});
