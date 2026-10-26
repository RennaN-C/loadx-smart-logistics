import { describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { listTrustedDevices, forgetCurrentDevice, revokeTrustedDevice, revokeAllTrustedDevices } from "./trustedDevicesApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), delete: vi.fn(), post: vi.fn() } }));
describe("contratos de confiança", () => {
  it("usa sessão/cookie central sem retornar credenciais nem usar Web Storage", async () => {
    const data = { enabled: true, lifetime_days: 30, items: [] };
    vi.mocked(api.get).mockResolvedValue({ data });
    expect(await listTrustedDevices()).toEqual(data);
    expect(api.get).toHaveBeenCalledWith("/auth/me/trusted-devices");
    await forgetCurrentDevice(); expect(api.delete).toHaveBeenCalledWith("/auth/me/trusted-devices/current");
    await revokeTrustedDevice("uuid"); expect(api.delete).toHaveBeenCalledWith("/auth/me/trusted-devices/uuid");
    await revokeAllTrustedDevices(); expect(api.post).toHaveBeenCalledWith("/auth/me/trusted-devices/revoke-all");
  });
});
