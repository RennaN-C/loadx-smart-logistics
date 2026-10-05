import { useEffect, useState } from "react";

const QUERY = "(prefers-color-scheme: dark)";

/**
 * O tema do LoadX sai só de `prefers-color-scheme` — não há alternador nem
 * `data-theme` (ver `app/styles.css`). A cena 3D não lê variável CSS, então
 * precisa perguntar a mesma coisa ao navegador.
 *
 * Reage à troca em tempo real: quem muda o tema do sistema com a tela aberta
 * veria um céu claro sobre uma página escura até recarregar.
 */
export function useDarkScheme(): boolean {
  const [dark, setDark] = useState(
    () => typeof matchMedia === "function" && matchMedia(QUERY).matches,
  );

  useEffect(() => {
    if (typeof matchMedia !== "function") return;

    const consulta = matchMedia(QUERY);
    const aoTrocar = (evento: MediaQueryListEvent) => setDark(evento.matches);

    consulta.addEventListener("change", aoTrocar);
    return () => consulta.removeEventListener("change", aoTrocar);
  }, []);

  return dark;
}
