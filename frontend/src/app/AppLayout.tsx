import { NotificationProvider } from "../features/notifications/components/NotificationProvider";
import { NotificationBell } from "../features/notifications/components/NotificationBell";
import { hasPermission } from "../features/auth/permissions";
import { canReadReports } from "../features/reports/permissions";
import { GlobalSearch } from "../features/global-search/components/GlobalSearch";
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { Avatar } from "../components/Avatar";
import { BrandMark, Icon, type IconName } from "../components/Icon";
import type { Role } from "../features/auth/types";
import { useAuth } from "../features/auth/hooks/useAuth";
import { activeSettingsSection, SETTINGS_SECTIONS } from "../features/settings/settingsSections";

interface NavItem {
  readonly to: string;
  readonly label: string;
  readonly icon: IconName;
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
/** Visão consolidada da operação inteira; o backend restringe a ADMIN e LOGISTICS_MANAGER. */
const OPERATION_OVERVIEW_READERS: readonly Role[] = ["ADMIN", "LOGISTICS_MANAGER"];
/** A API aplica isolamento de viagens/entregas de motorista ativo. */
const TRIP_READERS: readonly Role[] = ["ADMIN", "LOGISTICS_MANAGER", "DRIVER", "CUSTOM"];

const ALL_ROLES: readonly Role[] = ["ADMIN", "CHECKER", "LOGISTICS_MANAGER", "DRIVER", "CUSTOM"];

const ROLE_LABELS: Record<Role, string> = {
  CUSTOM: "Personalizado", ADMIN: "Administrador",
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
    items: [{ to: "/", label: "Visão geral", icon: "home", roles: ALL_ROLES }],
  },
  {
    id: "cadastros",
    title: "Cadastros",
    items: [
      { to: "/trucks", label: "Caminhões e frota", icon: "truck", roles: OPERATION_READERS },
      { to: "/products", label: "Produtos", icon: "package", roles: OPERATION_READERS },
      {
        to: "/contacts",
        label: "Clientes e motoristas",
        icon: "users",
        roles: PERSONAL_DATA_READERS,
      },
    ],
  },
  {
    id: "operacao",
    title: "Operação",
    items: [
      { to: "/orders", label: "Pedidos", icon: "orders", roles: OPERATION_READERS },
      { to: "/trips", label: "Viagens", icon: "truck", roles: TRIP_READERS },
      { to: "/loading-sessions", label: "Carregamentos", icon: "package", roles: OPERATION_READERS },
      { to: "/deliveries", label: "Entregas", icon: "truck", roles: TRIP_READERS },
      { to: "/planning", label: "Planejamento de carga", icon: "planning", roles: OPERATION_READERS },
      { to: "/reports", label: "Relatórios e indicadores", icon: "chart", roles: OPERATION_READERS },
      {
        to: "/audit",
        label: "Auditoria",
        icon: "report",
        roles: OPERATION_OVERVIEW_READERS,
      },
    ],
  },
  { id: "conta", title: "Minha conta", items: [{ to: "/account", label: "Meu perfil", icon: "users", roles: ALL_ROLES }] },
  {
    id: "administracao",
    title: "Administração",
    items: [{ to: "/settings", label: "Configurações", icon: "settings", roles: ["ADMIN"] }],
  },
];

const CUSTOM_NAV: Record<string, string[]> = { "/": ["loadx.customers.read", "loadx.products.read", "loadx.trucks.read", "loadx.drivers.read", "loadx.orders.read", "loadx.planning.read", "loadx.loading.read", "loadx.trips.read", "loadx.reports.read"], "/account": ["account"], "/trucks": ["loadx.trucks.read"], "/products": ["loadx.products.read"], "/contacts": ["loadx.customers.read", "loadx.drivers.read"], "/orders": ["loadx.orders.read"], "/planning": ["loadx.planning.read"], "/trips": ["loadx.trips.read", "loadx.trips.own"], "/loading-sessions": ["loadx.loading.read"], "/deliveries": ["loadx.deliveries.read", "loadx.trips.own"] };
const SIDEBAR_PREFERENCE = "loadx.sidebar-collapsed";

function initialSidebarCollapsed() {
  try {
    return window.localStorage.getItem(SIDEBAR_PREFERENCE) === "true";
  } catch {
    return false;
  }
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(initialSidebarCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);
  // Grupos com vários links funcionam como menus sanfonados independentes.
  // Começar com acordeões fechados evita poluição visual no primeiro acesso.
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    cadastros: false,
    operacao: false,
  });
  const [settingsSubmenuExpanded, setSettingsSubmenuExpanded] = useState(
    () => location.pathname === "/settings",
  );
  const mobileTriggerRef = useRef<HTMLButtonElement>(null);
  const mobileCloseRef = useRef<HTMLButtonElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_PREFERENCE, String(sidebarCollapsed));
    } catch {
      // Navegadores em modo restrito podem bloquear armazenamento; a navegação continua utilizável.
    }
  }, [sidebarCollapsed]);

  useEffect(() => {
    setMobileOpen(false);
    setSettingsSubmenuExpanded(location.pathname === "/settings");
  }, [location.pathname, location.search]);

  useEffect(() => {
    if (!mobileOpen) return;
    const originalOverflow = document.body.style.overflow;
    const mobileTrigger = mobileTriggerRef.current;
    document.body.style.overflow = "hidden";
    mobileCloseRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setMobileOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(sidebarRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not(:disabled), [tabindex]:not([tabindex="-1"])',
      ) ?? []).filter((element) => {
        const computed = window.getComputedStyle(element);
        return computed.display !== "none" && computed.visibility !== "hidden";
      });
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
      if (mobileTrigger?.isConnected) mobileTrigger.focus();
    };
  }, [mobileOpen]);


  // Esconder o link não substitui o backend, que continua barrando: evita só
  // oferecer um caminho que responderia 403. Grupo que esvazia some junto com o
  // título — o conferente não pode ver "Cadastros" sobre lugar nenhum.
  const groups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items
      .filter((item) => user !== null && (
        item.to === "/reports"
          ? canReadReports(user)
          : user.role === "CUSTOM"
            ? item.to === "/account" || (CUSTOM_NAV[item.to] ?? []).some((code) => hasPermission(user, code))
            : item.roles.includes(user.role)
      ))
      .map((item) => {
        if (item.to !== "/contacts") return item;
        const customers = hasPermission(user, "loadx.customers.read");
        const drivers = hasPermission(user, "loadx.drivers.read");
        return { ...item, label: customers && drivers ? item.label : customers ? "Clientes" : "Motoristas" };
      }),
  })).filter((group) => group.items.length > 0);

  return (
    <NotificationProvider active={Boolean(user)} key={`${user?.id}:${user?.role}:${user?.permissions?.join(",")}`}>
    <div className="app-shell" data-sidebar-collapsed={sidebarCollapsed} data-mobile-open={mobileOpen}>
      {/* o menu vem antes do conteúdo no DOM; sem isto, quem navega por teclado
          atravessa a lista inteira em toda troca de tela */}
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>

      <header className="app-mobile-topbar">
        <button
          type="button"
          ref={mobileTriggerRef}
          className="app-mobile-menu-button"
          aria-label="Abrir menu"
          aria-controls="loadx-side-navigation"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(true)}
        >
          <span aria-hidden="true">☰</span>
        </button>
        <span className="app-mobile-brand"><BrandMark size={24} /> LOADX</span>
      </header>

      {mobileOpen ? (
        <button
          type="button"
          className="app-sidebar-scrim"
          aria-label="Fechar o menu ao clicar fora"
          tabIndex={-1}
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <aside ref={sidebarRef} className="app-sidebar" aria-label="Menu lateral">
        <div className="app-sidebar-header">
          <p className="app-brand">
            <BrandMark size={27} />
            <span className="app-brand-label">LOADX</span>
          </p>
          <button
            type="button"
            className="app-sidebar-collapse"
            aria-controls="loadx-side-navigation"
            aria-expanded={!sidebarCollapsed}
            aria-label={sidebarCollapsed ? "Expandir menu lateral" : "Recolher menu lateral"}
            title={sidebarCollapsed ? "Expandir menu lateral" : "Recolher menu lateral"}
            onClick={() => setSidebarCollapsed((current) => !current)}
          >
            <span aria-hidden="true">{sidebarCollapsed ? "›" : "‹"}</span>
          </button>
          <button
            type="button"
            ref={mobileCloseRef}
            className="app-sidebar-close"
            aria-label="Fechar menu"
            onClick={() => setMobileOpen(false)}
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>

        {groups.length > 0 ? (
          <nav id="loadx-side-navigation" className="app-nav" aria-label="Navegação principal">
            {groups.map((group) => {
              const collapsible = group.items.length > 1;
              const expanded = expandedGroups[group.id] ?? true;
              const hasActivePage = group.items.some((item) =>
                location.pathname === item.to || (
                  item.to !== "/" && location.pathname.startsWith(`${item.to}/`)
                ),
              );
              return (
              <div key={group.id} className="app-nav-group" data-collapsible={collapsible}>
                {group.title ? collapsible ? (
                  <button
                    type="button"
                    className="app-nav-title app-nav-group-toggle"
                    id={`nav-${group.id}`}
                    aria-controls={`nav-group-items-${group.id}`}
                    aria-expanded={expanded && (!sidebarCollapsed || mobileOpen)}
                    data-active={hasActivePage}
                    title={sidebarCollapsed ? group.title : undefined}
                    onClick={() => {
                      if (sidebarCollapsed && !mobileOpen) {
                        setSidebarCollapsed(false);
                        setExpandedGroups((current) => ({ ...current, [group.id]: true }));
                      } else {
                        setExpandedGroups((current) => ({
                          ...current,
                          [group.id]: !(current[group.id] ?? true),
                        }));
                      }
                    }}
                  >
                    <Icon name={group.id === "cadastros" ? "package" : "planning"} size={16} />
                    <span className="app-nav-group-title">{group.title}</span>
                    <span className="app-nav-chevron" aria-hidden="true">⌄</span>
                  </button>
                ) : (
                  <p className="app-nav-title" id={`nav-${group.id}`}>{group.title}</p>
                ) : null}
                <ul
                  id={collapsible ? `nav-group-items-${group.id}` : undefined}
                  aria-labelledby={group.title ? `nav-${group.id}` : undefined}
                  hidden={collapsible && (!expanded || (sidebarCollapsed && !mobileOpen))}
                >
                  {group.items.map((item) => (
                    <li key={item.to}>
                      {/* `end` na raiz: sem isso o NavLink casa por prefixo e
                          "Início" ficaria marcado como ativo em todas as telas */}
                      <NavLink
                        to={item.to}
                        end={item.to === "/"}
                        aria-label={sidebarCollapsed ? item.label : undefined}
                        title={sidebarCollapsed ? item.label : undefined}
                        aria-expanded={item.to === "/settings" ? settingsSubmenuExpanded && (!sidebarCollapsed || mobileOpen) : undefined}
                        aria-controls={item.to === "/settings" ? "loadx-settings-submenu" : undefined}
                        onClick={(event) => {
                          if (item.to === "/settings") {
                            if (mobileOpen) {
                              // No drawer, tocar no pai expande/recolhe, sem sair da página.
                              event.preventDefault();
                              setSettingsSubmenuExpanded((expanded) => !expanded);
                              return;
                            }
                            if (sidebarCollapsed) {
                              // Abrir o trilho não deve apagar a subseção atualmente selecionada.
                              event.preventDefault();
                              setSidebarCollapsed(false);
                              setSettingsSubmenuExpanded(true);
                              return;
                            }
                            if (location.pathname === "/settings") {
                              // Alternar o submenu nunca remove o hash da seção atual.
                              event.preventDefault();
                            }
                            setSettingsSubmenuExpanded((expanded) => !expanded);
                          }
                          setMobileOpen(false);
                        }}
                      >
                        <Icon name={item.icon} size={17} />
                        <span className="app-nav-label">{item.label}</span>
                      </NavLink>
                      {item.to === "/settings" ? (
                        <ul
                          id="loadx-settings-submenu"
                          className="app-settings-submenu"
                          aria-label="Subseções de Configurações"
                          hidden={!settingsSubmenuExpanded || (sidebarCollapsed && !mobileOpen)}
                        >
                          {SETTINGS_SECTIONS.map((section) => (
                            <li key={section.id}>
                              <Link
                                to={`/settings#${section.id}`}
                                aria-current={location.pathname === "/settings" && activeSettingsSection(location.hash) === section.id ? "location" : undefined}
                                onClick={() => { setSettingsSubmenuExpanded(true); setMobileOpen(false); }}
                              >
                                {section.label}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
              );
            })}
          </nav>
        ) : null}

        {user ? (
          <div className="app-account">
            <Avatar name={user.name} size={34} />
            <span className="app-account-text">
              <span className="app-account-name">{user.name}</span>
              <span className="app-account-role">{ROLE_LABELS[user.role]}</span>
            </span>
            {/* só o ícone cabe ao lado do nome; o rótulo continua existindo para
                leitor de tela e vira dica ao parar o mouse em cima */}
            <button
              type="button"
              className="app-logout"
              title="Sair"
              onClick={() => void Promise.resolve(logout()).catch(() => undefined)}
            >
              <Icon name="logout" size={17} />
              <span className="sr-only">Sair</span>
            </button>
          </div>
        ) : null}
      </aside>

      <main id="conteudo">
        <header className="app-search-header"><GlobalSearch key={`${user?.id}:${user?.role}:${user?.permissions?.join(",")}`} />{user && <NotificationBell />}</header>
        <Outlet />
      </main>
    </div>
    </NotificationProvider>
  );
}
