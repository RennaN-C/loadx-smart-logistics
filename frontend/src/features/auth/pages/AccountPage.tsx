import { NotificationPreferences } from "../../notifications/components/NotificationPreferences";
import { AppearancePreferences } from "../components/AppearancePreferences";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { OwnProfileForm } from "../components/OwnProfileForm";
import { OwnPasswordForm } from "../components/OwnPasswordForm";
import { OwnSessionsPanel } from "../components/OwnSessionsPanel";
import "./AccountPage.css";
export function AccountPage() {
  const { updateUser } = useAuth();
  function signedOut(accountNotice: "password-changed" | "session-revoked") {
    updateUser(null, accountNotice);
  }
  return <div className="entity-page account-page"><header className="entity-header"><div><h1>Meu perfil</h1><p className="entity-lede">Gerencie seus dados, senha e sessões.</p></div><Link className="entity-header-link" to="/">Voltar ao início</Link></header>
    <section className="account-section" aria-labelledby="own-data"><h2 id="own-data">Dados pessoais</h2><OwnProfileForm /></section>
    <AppearancePreferences />
    <NotificationPreferences />
    <section className="account-section" aria-labelledby="own-security"><h2 id="own-security">Segurança</h2><OwnPasswordForm onSignedOut={signedOut} /></section>
    <section className="account-section" aria-labelledby="own-sessions"><h2 id="own-sessions">Sessões</h2><OwnSessionsPanel onSignedOut={signedOut} /></section>
    <p>Seus dados de conta e segurança ficam separados das configurações logísticas.</p>
  </div>;
}
