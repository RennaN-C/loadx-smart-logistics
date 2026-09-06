import { describe, expect, it } from "vitest";

import { createDevApiProxyOptions } from "./vite.config";

describe("createDevApiProxyOptions", () => {
  it.each([undefined, ""])(
    "não força Origin quando DEV_API_PROXY_ORIGIN é %s",
    (origin) => {
      expect(createDevApiProxyOptions("http://localhost:8000", origin)).toEqual({
        target: "http://localhost:8000",
      });
    },
  );

  it("encaminha exatamente o Origin configurado", () => {
    const origin = "https://frontend.example.test";

    expect(createDevApiProxyOptions("http://localhost:8000", origin)).toEqual({
      target: "http://localhost:8000",
      headers: { Origin: origin },
    });
  });
});
