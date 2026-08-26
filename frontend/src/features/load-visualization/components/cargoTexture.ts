import { CanvasTexture, SRGBColorSpace, type Texture } from "three";

/**
 * Textura de papelão desenhada em canvas, não carregada de imagem.
 *
 * O motivo é o orçamento: o chunk 3D está em 211 KiB gzip de 250 permitidos, e
 * um jogo de fotos de caixa comeria a folga inteira. Desenhando aqui o custo é
 * o do código — as mesmas contas que levaram o caminhão a ser construído em vez
 * de importado.
 *
 * Cada volume tem DUAS faces diferentes das outras: a de cima leva a fita, e a
 * da frente leva a etiqueta com o código do produto. As quatro restantes são
 * papelão liso. É isso que faz a carga parecer caixa empilhada, e não bloco.
 */

/** Lado da textura em pixels. 256 basta: o volume nunca ocupa a tela inteira. */
const SIZE = 256;

/** Papelão kraft, do claro ao escuro, para a granulação ter contraste. */
const KRAFT_LIGHT = "#c9a678";
const KRAFT = "#b8946a";
const KRAFT_DARK = "#9a7850";

type Face = "plain" | "tape" | "label";

/**
 * jsdom não tem canvas: a suíte de testes monta componentes que importam este
 * arquivo, então a ausência de contexto precisa devolver `null` em vez de
 * estourar. Sem textura o material cai na cor lisa, que é o comportamento antigo.
 */
function createCanvas(): CanvasRenderingContext2D | null {
  if (typeof document === "undefined") return null;

  const canvas = document.createElement("canvas");
  canvas.width = SIZE;
  canvas.height = SIZE;

  return canvas.getContext("2d");
}

/**
 * Ruído determinístico. `Math.random()` daria uma textura diferente a cada
 * render e faria a carga "ferver" entre quadros.
 */
function noiseAt(index: number): number {
  const value = Math.sin(index * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

function paintKraft(ctx: CanvasRenderingContext2D) {
  ctx.fillStyle = KRAFT;
  ctx.fillRect(0, 0, SIZE, SIZE);

  // fibra do papelão: riscos horizontais curtos, claros e escuros
  for (let i = 0; i < 1400; i += 1) {
    const x = noiseAt(i) * SIZE;
    const y = noiseAt(i + 7000) * SIZE;
    const comprimento = 2 + noiseAt(i + 3000) * 7;
    ctx.strokeStyle = noiseAt(i + 500) > 0.5 ? KRAFT_LIGHT : KRAFT_DARK;
    ctx.globalAlpha = 0.16 + noiseAt(i + 900) * 0.2;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + comprimento, y);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;

  // vinco das bordas: escurece a moldura para a quina do volume aparecer
  const borda = ctx.createLinearGradient(0, 0, 0, SIZE);
  borda.addColorStop(0, "rgba(60, 42, 24, 0.34)");
  borda.addColorStop(0.08, "rgba(60, 42, 24, 0)");
  borda.addColorStop(0.92, "rgba(60, 42, 24, 0)");
  borda.addColorStop(1, "rgba(60, 42, 24, 0.34)");
  ctx.fillStyle = borda;
  ctx.fillRect(0, 0, SIZE, SIZE);

  const lateral = ctx.createLinearGradient(0, 0, SIZE, 0);
  lateral.addColorStop(0, "rgba(60, 42, 24, 0.34)");
  lateral.addColorStop(0.08, "rgba(60, 42, 24, 0)");
  lateral.addColorStop(0.92, "rgba(60, 42, 24, 0)");
  lateral.addColorStop(1, "rgba(60, 42, 24, 0.34)");
  ctx.fillStyle = lateral;
  ctx.fillRect(0, 0, SIZE, SIZE);
}

function paintTape(ctx: CanvasRenderingContext2D) {
  // fenda das abas, no meio
  ctx.strokeStyle = "rgba(70, 50, 30, 0.5)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, SIZE / 2);
  ctx.lineTo(SIZE, SIZE / 2);
  ctx.stroke();

  // Fita por cima da fenda. Tom bem mais claro que o kraft de propósito: na
  // primeira versão ela ficou a 6 níveis de luminância do papelão e sumia.
  const topo = SIZE / 2 - 21;
  ctx.fillStyle = "rgba(226, 199, 152, 0.97)";
  ctx.fillRect(0, topo, SIZE, 42);

  // brilho do plástico na parte de cima da fita
  const brilho = ctx.createLinearGradient(0, topo, 0, topo + 42);
  brilho.addColorStop(0, "rgba(255, 255, 255, 0.42)");
  brilho.addColorStop(0.35, "rgba(255, 255, 255, 0.06)");
  brilho.addColorStop(1, "rgba(120, 92, 56, 0.14)");
  ctx.fillStyle = brilho;
  ctx.fillRect(0, topo, SIZE, 42);

  // bordas: é a linha que faz o olho ler "fita colada", e não "faixa pintada"
  ctx.strokeStyle = "rgba(108, 82, 48, 0.7)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, topo);
  ctx.lineTo(SIZE, topo);
  ctx.moveTo(0, topo + 42);
  ctx.lineTo(SIZE, topo + 42);
  ctx.stroke();
}

function paintLabel(ctx: CanvasRenderingContext2D, code: string) {
  const w = SIZE * 0.62;
  const h = SIZE * 0.3;
  const x = (SIZE - w) / 2;
  const y = SIZE * 0.3;

  ctx.fillStyle = "rgba(248, 246, 240, 0.96)";
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = "rgba(90, 70, 44, 0.5)";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(x, y, w, h);

  // faixa superior da etiqueta, onde vai o código
  ctx.fillStyle = "#1f2933";
  ctx.fillRect(x, y, w, h * 0.36);
  ctx.fillStyle = "#f8f6f0";
  ctx.font = `bold ${Math.round(h * 0.24)}px monospace`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(code.slice(0, 12), x + w / 2, y + h * 0.18);

  // código de barras fingido: o olho lê como etiqueta, e custa 20 traços
  const barTop = y + h * 0.46;
  const barBottom = y + h * 0.86;
  ctx.fillStyle = "#1f2933";
  let barX = x + 10;
  for (let i = 0; barX < x + w - 10; i += 1) {
    const largura = 1 + Math.round(noiseAt(i + 40) * 3);
    ctx.fillRect(barX, barTop, largura, barBottom - barTop);
    barX += largura + 1 + Math.round(noiseAt(i + 80) * 3);
  }
}

function buildTexture(face: Face, code: string): Texture | null {
  const ctx = createCanvas();
  if (ctx === null) return null;

  paintKraft(ctx);
  if (face === "tape") paintTape(ctx);
  if (face === "label") paintLabel(ctx, code);

  const texture = new CanvasTexture(ctx.canvas);
  // sem isto o papelão sai lavado: o canvas já entrega cor em sRGB
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

/**
 * Uma textura por código de produto, reaproveitada entre volumes iguais. Sem o
 * cache, uma carga de 200 volumes desenharia 600 canvas a cada montagem da cena.
 */
const cache = new Map<string, (Texture | null)[]>();

/**
 * Materiais na ordem que o `boxGeometry` do Three.js espera:
 * +X, -X, +Y (topo), -Y, +Z, -Z (frente, lado da porta do baú).
 */
export function cargoTextures(productCode: string): (Texture | null)[] {
  const cached = cache.get(productCode);
  if (cached) return cached;

  const plain = buildTexture("plain", productCode);
  const faces = [
    plain,
    plain,
    buildTexture("tape", productCode),
    plain,
    plain,
    buildTexture("label", productCode),
  ];

  cache.set(productCode, faces);
  return faces;
}

/** Libera as texturas da GPU. A cena chama ao desmontar. */
export function disposeCargoTextures() {
  for (const faces of cache.values()) {
    for (const texture of faces) texture?.dispose();
  }
  cache.clear();
}
