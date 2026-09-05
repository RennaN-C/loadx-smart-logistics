import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});

/**
 * O `Blob` do jsdom não implementa `text()`, que existe em todo navegador que
 * o projeto suporta. O remendo fica AQUI, no ambiente de teste, e não no
 * código de produção: carregar um `FileReader` na aplicação só para agradar o
 * jsdom colocaria no produto uma limitação que o produto não tem.
 */
if (typeof Blob.prototype.text !== "function") {
  Blob.prototype.text = function readAsText(this: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
      reader.onerror = () => reject(reader.error ?? new Error("Falha ao ler o Blob."));
      reader.readAsText(this);
    });
  };
}
