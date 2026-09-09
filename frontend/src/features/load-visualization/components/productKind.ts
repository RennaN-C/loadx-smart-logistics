/**
 * Descobre O QUE é o produto a partir do nome cadastrado, para a visualização
 * desenhar uma TV como TV em vez de mais uma caixa de papelão.
 *
 * `PENDENTE DE DEFINIÇÃO`: o produto não tem campo de categoria no backend
 * (`products/schemas.py` traz código, nome, descrição, medidas, peso e as três
 * flags do otimizador). Enquanto não existir, a classificação sai do nome por
 * palavra-chave. É heurística e assumidamente falível: "TV" no nome acerta,
 * "modelo XPT-42" não. Quando a equipe adicionar `category`, este arquivo passa
 * a ler o campo e as palavras-chave viram só o fallback.
 *
 * Isto é APARÊNCIA, não geometria. O volume continua sendo a caixa que o
 * otimizador reservou — mudar a forma faria a tela mentir sobre o espaço
 * ocupado, que é a razão de ela existir (`docs/11`).
 */
export type ProductKind = "tv" | "fridge" | "stove" | "washer" | "microwave" | "box";

/**
 * Ordem importa: a primeira que casar vence. "forno de micro-ondas" precisa
 * bater em micro-ondas antes de bater em forno.
 */
const KEYWORDS: readonly (readonly [ProductKind, readonly string[]])[] = [
  ["microwave", ["microondas", "micro ondas", "microonda"]],
  ["tv", ["tv", "televisao", "televisor", "monitor", "smart tv"]],
  ["fridge", ["geladeira", "refrigerador", "frigobar", "freezer", "expositor"]],
  ["washer", ["lavadora", "lava roupas", "lava loucas", "lavaloucas", "maquina de lavar", "secadora"]],
  ["stove", ["fogao", "cooktop", "forno"]],
];

/**
 * Minúsculas e sem acento, para "Televisão" e "TELEVISAO" caírem no mesmo lugar.
 * Pontuação vira espaço: "micro-ondas" e "micro ondas" são a mesma coisa.
 */
function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Casa por PALAVRA INTEIRA. Sem isto, "tv" acharia a si mesmo dentro de
 * qualquer código de produto que contivesse essas letras.
 */
function hasTerm(haystack: string, term: string): boolean {
  const words = haystack.split(" ");
  const termWords = term.split(" ");

  for (let i = 0; i + termWords.length <= words.length; i += 1) {
    if (termWords.every((word, offset) => words[i + offset] === word)) return true;
  }

  return false;
}

export function classifyProduct(productName: string): ProductKind {
  const name = normalize(productName);

  for (const [kind, terms] of KEYWORDS) {
    if (terms.some((term) => hasTerm(name, normalize(term)))) return kind;
  }

  return "box";
}
