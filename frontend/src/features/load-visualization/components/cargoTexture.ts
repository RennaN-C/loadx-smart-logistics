import { CanvasTexture, SRGBColorSpace, type Texture } from "three";

import type { ProductKind } from "./productKind";

/**
 * Aparência dos volumes, desenhada em canvas e não carregada de imagem.
 *
 * O motivo é o orçamento: o chunk 3D tem 250 KiB gzip e está em 212. Um jogo de
 * fotos de TV, geladeira e fogão comeria a folga inteira — a mesma conta que
 * levou o caminhão a ser construído em vez de importado. Desenhando aqui, cada
 * tipo novo custa algumas dezenas de linhas e zero byte de asset.
 *
 * A FORMA continua sendo a caixa que o otimizador reservou. Só a superfície
 * muda: uma TV é um paralelepípedo com cara de TV, não um modelo de TV. Mudar a
 * geometria faria a tela mentir sobre o espaço ocupado (`docs/11`).
 */

/** Lado da textura em pixels. 256 basta: o volume nunca ocupa a tela inteira. */
const SIZE = 256;

const KRAFT_LIGHT = "#c9a678";
const KRAFT = "#b8946a";
const KRAFT_DARK = "#9a7850";

/**
 * jsdom não tem canvas: a suíte monta componentes que importam este arquivo,
 * então a ausência de contexto devolve `null` em vez de estourar. Sem textura o
 * material cai na cor lisa.
 */
function createCanvas(): CanvasRenderingContext2D | null {
  if (typeof document === "undefined") return null;

  const canvas = document.createElement("canvas");
  canvas.width = SIZE;
  canvas.height = SIZE;

  return canvas.getContext("2d");
}

/**
 * Ruído determinístico. `Math.random()` daria textura diferente a cada render e
 * faria a carga "ferver" entre quadros.
 */
function noiseAt(index: number): number {
  const value = Math.sin(index * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

/** Escurece a moldura, para a quina do volume aparecer sem depender da luz. */
function paintEdges(ctx: CanvasRenderingContext2D, strength = 0.34) {
  for (const horizontal of [false, true]) {
    const gradient = horizontal
      ? ctx.createLinearGradient(0, 0, SIZE, 0)
      : ctx.createLinearGradient(0, 0, 0, SIZE);
    gradient.addColorStop(0, `rgba(20, 16, 10, ${strength})`);
    gradient.addColorStop(0.08, "rgba(20, 16, 10, 0)");
    gradient.addColorStop(0.92, "rgba(20, 16, 10, 0)");
    gradient.addColorStop(1, `rgba(20, 16, 10, ${strength})`);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, SIZE, SIZE);
  }
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
  paintEdges(ctx);
}

function paintTape(ctx: CanvasRenderingContext2D) {
  const topo = SIZE / 2 - 21;

  // fenda das abas
  ctx.strokeStyle = "rgba(70, 50, 30, 0.5)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, SIZE / 2);
  ctx.lineTo(SIZE, SIZE / 2);
  ctx.stroke();

  // Fita bem mais clara que o kraft de propósito: a 6 níveis de luminância ela
  // some, foi o que aconteceu na primeira versão.
  ctx.fillStyle = "rgba(226, 199, 152, 0.97)";
  ctx.fillRect(0, topo, SIZE, 42);

  const brilho = ctx.createLinearGradient(0, topo, 0, topo + 42);
  brilho.addColorStop(0, "rgba(255, 255, 255, 0.42)");
  brilho.addColorStop(0.35, "rgba(255, 255, 255, 0.06)");
  brilho.addColorStop(1, "rgba(120, 92, 56, 0.14)");
  ctx.fillStyle = brilho;
  ctx.fillRect(0, topo, SIZE, 42);

  ctx.strokeStyle = "rgba(108, 82, 48, 0.7)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, topo);
  ctx.lineTo(SIZE, topo);
  ctx.moveTo(0, topo + 42);
  ctx.lineTo(SIZE, topo + 42);
  ctx.stroke();
}

/** Chapa lisa: base das laterais de eletrodoméstico. */
function paintPanel(ctx: CanvasRenderingContext2D, base: string, brilhoTopo: number) {
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, SIZE, SIZE);

  const luz = ctx.createLinearGradient(0, 0, SIZE * 0.7, SIZE);
  luz.addColorStop(0, `rgba(255, 255, 255, ${brilhoTopo})`);
  luz.addColorStop(0.55, "rgba(255, 255, 255, 0.02)");
  luz.addColorStop(1, "rgba(0, 0, 0, 0.1)");
  ctx.fillStyle = luz;
  ctx.fillRect(0, 0, SIZE, SIZE);

  paintEdges(ctx, 0.22);
}

function paintScreen(ctx: CanvasRenderingContext2D) {
  paintPanel(ctx, "#22262b", 0.06);

  // moldura fina e tela quase preta
  const m = SIZE * 0.06;
  ctx.fillStyle = "#0b0d10";
  ctx.fillRect(m, m, SIZE - m * 2, SIZE - m * 2.8);

  // reflexo diagonal: é o que faz o olho ler "vidro" e não "buraco"
  const reflexo = ctx.createLinearGradient(m, m, SIZE - m, SIZE - m);
  reflexo.addColorStop(0, "rgba(150, 180, 220, 0.22)");
  reflexo.addColorStop(0.35, "rgba(150, 180, 220, 0.04)");
  reflexo.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.fillStyle = reflexo;
  ctx.fillRect(m, m, SIZE - m * 2, SIZE - m * 2.8);

  // pé/barra inferior e ponto do led
  ctx.fillStyle = "#2c3138";
  ctx.fillRect(SIZE * 0.36, SIZE - m * 1.9, SIZE * 0.28, m * 0.7);
  ctx.fillStyle = "#7ed0a0";
  ctx.beginPath();
  ctx.arc(SIZE / 2, SIZE - m * 1.2, 2.6, 0, Math.PI * 2);
  ctx.fill();
}

function paintFridgeFront(ctx: CanvasRenderingContext2D) {
  paintPanel(ctx, "#d6d9dc", 0.28);

  // fresta entre freezer e refrigerador
  ctx.fillStyle = "rgba(70, 76, 82, 0.55)";
  ctx.fillRect(0, SIZE * 0.32, SIZE, 3);

  // puxador vertical comprido, do lado esquerdo das duas portas
  ctx.fillStyle = "#8a9099";
  ctx.fillRect(SIZE * 0.14, SIZE * 0.06, 7, SIZE * 0.2);
  ctx.fillRect(SIZE * 0.14, SIZE * 0.4, 7, SIZE * 0.44);
  ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
  ctx.fillRect(SIZE * 0.14, SIZE * 0.06, 2.5, SIZE * 0.2);
  ctx.fillRect(SIZE * 0.14, SIZE * 0.4, 2.5, SIZE * 0.44);
}

function paintStoveTop(ctx: CanvasRenderingContext2D) {
  paintPanel(ctx, "#1b1e22", 0.05);

  // quatro bocas
  for (const [cx, cy, r] of [
    [SIZE * 0.3, SIZE * 0.3, SIZE * 0.12],
    [SIZE * 0.7, SIZE * 0.3, SIZE * 0.09],
    [SIZE * 0.3, SIZE * 0.7, SIZE * 0.09],
    [SIZE * 0.7, SIZE * 0.7, SIZE * 0.12],
  ]) {
    ctx.strokeStyle = "rgba(190, 196, 204, 0.55)";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "rgba(120, 128, 138, 0.35)";
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.32, 0, Math.PI * 2);
    ctx.fill();
  }
}

function paintStoveFront(ctx: CanvasRenderingContext2D) {
  paintPanel(ctx, "#c9ccd0", 0.24);

  // painel de botões
  ctx.fillStyle = "#2a2e33";
  ctx.fillRect(0, 0, SIZE, SIZE * 0.2);
  for (let i = 0; i < 4; i += 1) {
    ctx.fillStyle = "#c9ccd0";
    ctx.beginPath();
    ctx.arc(SIZE * (0.18 + i * 0.21), SIZE * 0.1, SIZE * 0.035, 0, Math.PI * 2);
    ctx.fill();
  }

  // visor do forno
  ctx.fillStyle = "#15181c";
  ctx.fillRect(SIZE * 0.1, SIZE * 0.32, SIZE * 0.8, SIZE * 0.46);
  ctx.fillStyle = "rgba(150, 180, 220, 0.12)";
  ctx.fillRect(SIZE * 0.1, SIZE * 0.32, SIZE * 0.8, SIZE * 0.12);
  ctx.fillStyle = "#8a9099";
  ctx.fillRect(SIZE * 0.08, SIZE * 0.24, SIZE * 0.84, 6);
}

function paintWasherFront(ctx: CanvasRenderingContext2D) {
  paintPanel(ctx, "#dfe2e5", 0.3);

  // painel superior
  ctx.fillStyle = "#c2c7cc";
  ctx.fillRect(0, 0, SIZE, SIZE * 0.18);
  ctx.fillStyle = "#596068";
  ctx.beginPath();
  ctx.arc(SIZE * 0.82, SIZE * 0.09, SIZE * 0.04, 0, Math.PI * 2);
  ctx.fill();

  // escotilha
  const cx = SIZE / 2;
  const cy = SIZE * 0.56;
  ctx.fillStyle = "#aeb4ba";
  ctx.beginPath();
  ctx.arc(cx, cy, SIZE * 0.27, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#1c2024";
  ctx.beginPath();
  ctx.arc(cx, cy, SIZE * 0.21, 0, Math.PI * 2);
  ctx.fill();
  const vidro = ctx.createLinearGradient(cx - SIZE * 0.2, cy - SIZE * 0.2, cx, cy);
  vidro.addColorStop(0, "rgba(170, 200, 235, 0.3)");
  vidro.addColorStop(1, "rgba(170, 200, 235, 0)");
  ctx.fillStyle = vidro;
  ctx.beginPath();
  ctx.arc(cx, cy, SIZE * 0.21, 0, Math.PI * 2);
  ctx.fill();
}

function paintMicrowaveFront(ctx: CanvasRenderingContext2D) {
  paintPanel(ctx, "#2b2f34", 0.08);

  // porta com grade
  ctx.fillStyle = "#101317";
  ctx.fillRect(SIZE * 0.07, SIZE * 0.16, SIZE * 0.58, SIZE * 0.68);
  ctx.strokeStyle = "rgba(150, 160, 172, 0.18)";
  ctx.lineWidth = 1;
  for (let i = 1; i < 10; i += 1) {
    const passo = (SIZE * 0.58) / 10;
    ctx.beginPath();
    ctx.moveTo(SIZE * 0.07 + i * passo, SIZE * 0.16);
    ctx.lineTo(SIZE * 0.07 + i * passo, SIZE * 0.84);
    ctx.stroke();
  }
  ctx.fillStyle = "rgba(160, 190, 225, 0.12)";
  ctx.fillRect(SIZE * 0.07, SIZE * 0.16, SIZE * 0.58, SIZE * 0.18);

  // painel lateral
  ctx.fillStyle = "#1c2024";
  ctx.fillRect(SIZE * 0.7, SIZE * 0.16, SIZE * 0.23, SIZE * 0.68);
  ctx.fillStyle = "#63d19a";
  ctx.fillRect(SIZE * 0.73, SIZE * 0.21, SIZE * 0.17, SIZE * 0.09);
  for (let linha = 0; linha < 4; linha += 1) {
    for (let col = 0; col < 3; col += 1) {
      ctx.fillStyle = "#454b52";
      ctx.fillRect(SIZE * (0.735 + col * 0.058), SIZE * (0.4 + linha * 0.1), SIZE * 0.04, SIZE * 0.06);
    }
  }
}

/** Faces na ordem do `boxGeometry`: +X, -X, +Y (topo), -Y, +Z (frente), -Z. */
type Painter = (ctx: CanvasRenderingContext2D) => void;

function facePainters(kind: ProductKind): readonly [Painter, Painter, Painter, Painter, Painter, Painter] {
  const kraft: Painter = paintKraft;
  const caixaTopo: Painter = (ctx) => {
    paintKraft(ctx);
    paintTape(ctx);
  };

  switch (kind) {
    case "tv": {
      const costas: Painter = (ctx) => paintPanel(ctx, "#31363c", 0.08);
      return [costas, costas, costas, costas, paintScreen, costas];
    }
    case "fridge": {
      const lado: Painter = (ctx) => paintPanel(ctx, "#cfd3d7", 0.22);
      return [lado, lado, lado, lado, paintFridgeFront, lado];
    }
    case "stove": {
      const lado: Painter = (ctx) => paintPanel(ctx, "#c2c6ca", 0.2);
      return [lado, lado, paintStoveTop, lado, paintStoveFront, lado];
    }
    case "washer": {
      const lado: Painter = (ctx) => paintPanel(ctx, "#d8dbde", 0.24);
      return [lado, lado, lado, lado, paintWasherFront, lado];
    }
    case "microwave": {
      const lado: Painter = (ctx) => paintPanel(ctx, "#2f343a", 0.1);
      return [lado, lado, lado, lado, paintMicrowaveFront, lado];
    }
    default:
      return [kraft, kraft, caixaTopo, kraft, kraft, kraft];
  }
}

function buildTexture(paint: Painter): Texture | null {
  const ctx = createCanvas();
  if (ctx === null) return null;

  paint(ctx);

  const texture = new CanvasTexture(ctx.canvas);
  // sem isto a superfície sai lavada: o canvas já entrega cor em sRGB
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

/**
 * Uma leva de texturas por TIPO, não por produto: mil caixas de papelão
 * compartilham as mesmas seis. Sem o cache, uma carga de 200 volumes desenharia
 * 1200 canvas a cada montagem da cena.
 *
 * O cache vive enquanto a aba viver, e NÃO é descartado ao desmontar a cena. O
 * teto é a quantidade de tipos, que é constante: seis faces por tipo, seis
 * tipos, nunca cresce com o tamanho da carga. Liberar isso num efeito criava um
 * problema pior — o StrictMode monta, desmonta e remonta, então o descarte
 * rodava no meio e deixava material apontando para textura já liberada.
 */
const cache = new Map<ProductKind, (Texture | null)[]>();

export function cargoTextures(kind: ProductKind): (Texture | null)[] {
  const cached = cache.get(kind);
  if (cached) return cached;

  const faces = facePainters(kind).map(buildTexture);
  cache.set(kind, faces);
  return faces;
}
