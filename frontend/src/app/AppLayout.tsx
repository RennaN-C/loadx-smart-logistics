import { NavLink, Outlet } from "react-router-dom";

import type { Role } from "../features/auth/types";
import { useAuth } from "../features/auth/hooks/useAuth";

interface NavItem {
  readonly to: string;
  readonly label: string;
  /** Perfis que conseguem LER o recurso, espelhando o require_roles do backend. */
  readonly roles: readonly Role[];
}

interface NavGroup {
  readonly id: string;
  /** null no grupo de abertura: um título para um item só seria ruído. */
  readonly title: string | null;
  readonly items: readonly NavItem[];
}

const OPERATION_READERS: readonly Role[] = ["ADMIN", "CHECKER", "LOGISTICS_MANAGER"];
/** Clientes e motoristas são dados pessoais: CHECKER não lê (ver docs/04). */
const PERSONAL_DATA_READERS: readonly Role[] = ["ADMIN", "LOGISTICS_MANAGER"];

const ALL_ROLES: readonly Role[] = ["ADMIN", "CHECKER", "LOGISTICS_MANAGER", "DRIVER"];

const ROLE_LABELS: Record<Role, string> = {
  ADMIN: "Administrador",
  LOGISTICS_MANAGER: "Gestor de logística",
  CHECKER: "Conferente",
  DRIVER: "Motorista",
};

/**
 * A vertical comporta agrupamento, que a barra no topo não comportava. A divisão
 * segue a operação: o que se cadastra uma vez e o que se movimenta todo dia.
 */
const NAV_GROUPS: readonly NavGroup[] = [
  {
    id: "inicio",
    title: null,
    items: [{ to: "/", label: "Início", roles: ALL_ROLES }],
  },
  {
    id: "cadastros",
    title: "Cadastros",
    items: [
      { to: "/trucks", label: "Caminhões", roles: OPERATION_READERS },
      { to: "/products", label: "Produtos", roles: OPERATION_READERS },
      { to: "/contacts", label: "Clientes e motoristas", roles: PERSONAL_DATA_READERS },
    ],
  },
  {
    id: "operacao",
    title: "Operação",
    items: [
      { to: "/orders", label: "Pedidos", roles: OPERATION_READERS },
      { to: "/planning", label: "Planejamento", roles: OPERATION_READERS },
    ],
  },
];

export function AppLayout() {
  const { user, logout } = useAuth();

  // Esconder o link não substitui o backend, que continua barrando: evita só
  // oferecer um caminho que responderia 403. Grupo que esvazia some junto com o
  // título — o conferente não pode ver "Cadastros" sobre lugar nenhum.
  const groups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => user !== null && item.roles.includes(user.role)),
  })).filter((group) => group.items.length > 0);

  return (
    <div className="app-shell">
      {/* o menu vem antes do conteúdo no DOM; sem isto, quem navega por teclado
          atravessa a lista inteira em toda troca de tela */}
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>

      <aside className="app-sidebar">
        <p className="eyebrow app-brand">LOADX</p>

        {groups.length > 0 ? (
          <nav className="app-nav" aria-label="Navegação principal">
            {groups.map((group) => (
              <div key={group.id} className="app-nav-group">
                {group.title ? (
                  <p className="app-nav-title" id={`nav-${group.id}`}>
                    {group.title}
                  </p>
                ) : null}
                <ul aria-labelledby={group.title ? `nav-${group.id}` : undefined}>
                  {group.items.map((item) => (
                    <li key={item.to}>
                      {/* `end` na raiz: sem isso o NavLink casa por prefixo e
                          "Início" ficaria marcado como ativo em todas as telas */}
                      <NavLink to={item.to} end={item.to === "/"}>
                        {item.label}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        ) : null}

        {user ? (
          <div className="app-account">
            <span className="app-account-name">{user.name}</span>
            <span className="app-account-role">{ROLE_LABELS[user.role]}</span>
            <button
              type="button"
              className="app-logout"
              onClick={() => void Promise.resolve(logout()).catch(() => undefined)}
            >
              Sair
            </button>
          </div>
        ) : null}
      </aside>

      <main id="conteudo">
        <Outlet />
      </main>
    </div>
  );
}
