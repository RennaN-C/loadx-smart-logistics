import { NavLink, Outlet } from "react-router-dom";

import type { Role } from "../features/auth/types";
import { useAuth } from "../features/auth/hooks/useAuth";

interface NavItem {
  readonly to: string;
  readonly label: string;
  /** Perfis que conseguem LER o recurso, espelhando o require_roles do backend. */
  readonly roles: readonly Role[];
}

const OPERATION_READERS: readonly Role[] = ["ADMIN", "CHECKER", "LOGISTICS_MANAGER"];
/** Clientes e motoristas são dados pessoais: CHECKER não lê (ver docs/04). */
const PERSONAL_DATA_READERS: readonly Role[] = ["ADMIN", "LOGISTICS_MANAGER"];

const NAV_ITEMS: readonly NavItem[] = [
  { to: "/trucks", label: "Caminhões", roles: OPERATION_READERS },
  { to: "/products", label: "Produtos", roles: OPERATION_READERS },
  { to: "/contacts", label: "Clientes e motoristas", roles: PERSONAL_DATA_READERS },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  // Esconder o link não substitui o backend, que continua barrando: evita só
  // oferecer um caminho que responderia 403.
  const visibleItems = NAV_ITEMS.filter((item) => user !== null && item.roles.includes(user.role));

  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="eyebrow">LOADX</p>
        {visibleItems.length > 0 ? (
          <nav className="app-nav">
            {visibleItems.map((item) => (
              <NavLink key={item.to} to={item.to}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        ) : null}
        {user ? (
          <div className="app-header-account">
            <span>{user.name}</span>
            <button type="button" className="app-header-logout" onClick={logout}>
              Sair
            </button>
          </div>
        ) : null}
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
