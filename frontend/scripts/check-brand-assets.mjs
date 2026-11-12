import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const files = [
  ["favicon-16.png", 16],
  ["favicon-32.png", 32],
  ["loadx-mark-128.png", 128],
];

for (const [name, size] of files) {
  const data = readFileSync(new URL(`../public/branding/${name}`, import.meta.url));
  assert.equal(data.subarray(0, 8).toString("hex"), "89504e470d0a1a0a", `${name}: PNG inválido`);
  assert.equal(data.readUInt32BE(16), size, `${name}: largura incorreta`);
  assert.equal(data.readUInt32BE(20), size, `${name}: altura incorreta`);
  assert.ok(data.length < 100_000, `${name}: imagem acima de 100 KB`);
}

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
for (const name of ["favicon-16.png", "favicon-32.png"]) {
  assert.ok(html.includes(`/branding/${name}`), `Falta referência a ${name} no HTML`);
}
const component = readFileSync(new URL("../src/components/Icon.tsx", import.meta.url), "utf8");
assert.ok(component.includes("/branding/loadx-mark-128.png"), "Marca oficial ausente do BrandMark");
const loginArtName = "login-reference-left.avif";
const loginArt = readFileSync(new URL(`../public/images/${loginArtName}`, import.meta.url));
assert.equal(loginArt.toString("ascii", 4, 8), "ftyp", `${loginArtName}: ISOBMFF inválido`);
assert.equal(loginArt.toString("ascii", 8, 12), "avif", `${loginArtName}: assinatura AVIF inválida`);
assert.ok(loginArt.length >= 25_000 && loginArt.length < 350_000, `${loginArtName}: tamanho inesperado`);
const brandPanel = readFileSync(new URL("../src/features/auth/components/BrandPanel.tsx", import.meta.url), "utf8");
assert.ok(brandPanel.includes(`/images/${loginArtName}`), "Arte aprovada não referenciada pelo login");
assert.ok(!brandPanel.includes("login-world-map"), "Overlay artificial do mapa voltou ao login");
console.log("Identidade LoadX: favicons, BrandMark e arte AVIF do login validados.");
