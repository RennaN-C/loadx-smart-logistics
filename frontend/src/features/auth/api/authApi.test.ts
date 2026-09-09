import { describe, expect, it } from "vitest";

import { mapUserFromDto } from "./authApi";

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
