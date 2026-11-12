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
const loginArtName = "login-cinematic-scene-hd.webp";
const loginArt = readFileSync(new URL(`../public/images/${loginArtName}`, import.meta.url));
assert.equal(loginArt.toString("ascii", 0, 4), "RIFF", `${loginArtName}: RIFF inválido`);
assert.equal(loginArt.toString("ascii", 8, 12), "WEBP", `${loginArtName}: WebP inválido`);
assert.ok(loginArt.length >= 180_000 && loginArt.length < 750_000, `${loginArtName}: tamanho inesperado`);
const vp8Header = loginArt.indexOf(Buffer.from([0x9d, 0x01, 0x2a]));
assert.ok(vp8Header >= 0 && vp8Header + 7 <= loginArt.length, `${loginArtName}: cabecalho VP8 invalido`);
assert.equal(loginArt.readUInt16LE(vp8Header + 3) & 0x3fff, 1800, `${loginArtName}: largura inesperada`);
assert.equal(loginArt.readUInt16LE(vp8Header + 5) & 0x3fff, 2000, `${loginArtName}: altura inesperada`);
const brandPanel = readFileSync(new URL("../src/features/auth/components/BrandPanel.tsx", import.meta.url), "utf8");
assert.ok(brandPanel.includes(`/images/${loginArtName}`), "Cena cinematográfica não referenciada pelo login");
console.log("Identidade LoadX: favicons, HTML BrandMark e cena de login validados.");
