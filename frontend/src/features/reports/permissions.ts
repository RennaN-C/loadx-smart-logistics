import type { Role } from "../auth/types";

/**
 * Quem enxerga os botões de relatório.
 *
 * Espelha o `require_roles("ADMIN", "LOGISTICS_MANAGER")` de
 * `backend/app/modules/reports/router.py`. Esconder o botão não substitui o
 * backend, que continua barrando — evita só oferecer um caminho que
 * responderia 403.
 *
 * `Set` em vez de array porque a checagem roda a cada render das duas telas
 * que a usam, e porque centralizar aqui impede que as duas listas divirjam.
 */
const REPORT_READERS = new Set<Role>(["ADMIN", "LOGISTICS_MANAGER"]);

export function canReadReports(role: Role | undefined): boolean {
  return role !== undefined && REPORT_READERS.has(role);
}
