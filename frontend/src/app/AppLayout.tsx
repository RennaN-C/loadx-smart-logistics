import { Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="eyebrow">LOADX</p>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
