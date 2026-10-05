/**
 * Props que o CONTROLE precisa receber para o erro do `FormField` ser anunciado.
 *
 * Mora fora do `FormField.tsx` por dois motivos. O primeiro é a regra do Fast
 * Refresh: um arquivo que exporta componente e função perde o hot reload. O
 * segundo é que injetar essas props no children exigiria `cloneElement`, que
 * funciona até alguém envolver o input num fragmento — aí a ligação some sem
 * erro nenhum. Aqui o TypeScript cobra no lugar certo.
 */
export function fieldErrorProps(
  id: string,
  error: string | null | undefined,
): { "aria-invalid"?: true; "aria-describedby"?: string } {
  return error ? { "aria-invalid": true, "aria-describedby": `${id}-error` } : {};
}
