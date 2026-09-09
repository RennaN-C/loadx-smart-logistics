/**
 * Iniciais para o avatar. Duas letras no máximo — três já viram borrão a 32px.
 * Nome composto usa a primeira e a ÚLTIMA palavra, que é como se abrevia gente
 * em português: "Ana Maria Souza" vira AS, não AM.
 *
 * Fica fora de `Avatar.tsx` porque arquivo que exporta componente e função
 * junto derruba o Fast Refresh do Vite.
 */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}
