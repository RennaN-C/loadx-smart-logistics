import { Outlet } from "react-router-dom";

import { useAuth } from "../features/auth/hooks/useAuth";

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="eyebrow">LOADX</p>
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
