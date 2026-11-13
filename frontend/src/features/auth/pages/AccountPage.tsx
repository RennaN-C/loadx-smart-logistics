import { NotificationPreferences } from "../../notifications/components/NotificationPreferences";
import { AppearancePreferences } from "../components/AppearancePreferences";
import { Link, useSearchParams } from "react-router-dom";
import { Tabs } from "../../../components/Tabs";
import { useAuth } from "../hooks/useAuth";
import { OwnProfileForm } from "../components/OwnProfileForm";
import { TrustedDevicesPanel } from "../components/TrustedDevicesPanel";
import { OwnMfaPanel } from "../components/OwnMfaPanel";

import { OwnPasswordForm } from "../components/OwnPasswordForm";
import { OwnSessionsPanel } from "../components/OwnSessionsPanel";
import "./AccountPage.css";
export function AccountPage() {
  const { updateUser, user } = useAuth();
  const [params, setParams] = useSearchParams();
  const active = ACCOUNT_TABS.find((tab) => tab.id === params.get("tab"))?.id ?? "data";
  function selectTab(tab: string) {
    const next = new URLSearchParams(params);
    next.set("tab", tab);
    setParams(next);
  }
  function signedOut(accountNotice: "password-changed" | "session-revoked") {
    updateUser(null, accountNotice);
  }
  return <div className="entity-page account-page"><header className="entity-header"><div><p className="overview-eyebrow">Minha conta</p><h1>Meu perfil</h1><p className="entity-lede">Gerencie seus dados, senha e sessões.</p></div><Link className="entity-header-link" to="/">Voltar ao início</Link></header>
    <Tabs items={ACCOUNT_TABS} active={active} onChange={selectTab} label="Seções do perfil" />
    <div role="tabpanel" id="panel-data" aria-labelledby="tab-data" hidden={active !== "data"}>
    <div className="account-identity-summary" aria-label="Identidade da conta">
      <div><span>Conta conectada</span><strong>{user?.name}</strong><small>{user?.email}</small></div>
      <div><span>Perfil de acesso</span><strong>{user ? { CUSTOM: "Personalizado", ADMIN: "Administrador", LOGISTICS_MANAGER: "Gestor de logística", CHECKER: "Conferente", DRIVER: "Motorista" }[user.role] : ""}</strong><small>Definido pela administração</small></div>
    </div>
    <section className="account-section" aria-labelledby="own-data"><h2 id="own-data">Dados pessoais</h2><OwnProfileForm /></section>
    </div>
    <div role="tabpanel" id="panel-preferences" aria-labelledby="tab-preferences" hidden={active !== "preferences"}>
      {active === "preferences" ? <div className="account-preferences-content"><AppearancePreferences /><NotificationPreferences /></div> : null}
    </div>
    <div role="tabpanel" id="panel-security" aria-labelledby="tab-security" hidden={active !== "security"}>
    <section className="account-section" aria-labelledby="own-security"><h2 id="own-security">Segurança</h2><OwnMfaPanel /><OwnPasswordForm onSignedOut={signedOut} /></section>
    </div>
    <div role="tabpanel" id="panel-sessions" aria-labelledby="tab-sessions" hidden={active !== "sessions"}>
    <section className="account-section" aria-labelledby="own-sessions"><h2 id="own-sessions">Sessões</h2><OwnSessionsPanel onSignedOut={signedOut} /></section>
    <TrustedDevicesPanel />
    </div>
  </div>;
}

const ACCOUNT_TABS = [
  { id: "data", label: "Dados pessoais" },
  { id: "preferences", label: "Preferências" },
  { id: "security", label: "Segurança e MFA" },
  { id: "sessions", label: "Sessões e dispositivos" },
] as const;
