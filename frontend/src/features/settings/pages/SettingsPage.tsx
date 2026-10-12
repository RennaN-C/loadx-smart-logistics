import { Link, useLocation } from "react-router-dom";
import { activeSettingsSection } from "../settingsSections";
import { useAuth } from "../../auth/hooks/useAuth";
import { CompanyProfileForm } from "../components/CompanyProfileForm";
import { IntegrationHealthPanel } from "../components/IntegrationHealthPanel";
import { SettingsSection } from "../components/SettingsSection";
import "./SettingsPage.css";

const UPCOMING_ACCOUNT_SECTIONS = [
  { id: "users", title: "Gestão de usuários", description: "Cadastro e gestão de acesso dos usuários do LoadX." },
] as const;

export function SettingsPage() {
  const { user } = useAuth();
  const { hash } = useLocation();
  const activeSection = activeSettingsSection(hash);
  if (!user) return null;

  return (
    <div className="entity-page settings-page">
      <header className="entity-header">
        <div>
          <h1>Configurações</h1>
          <p className="entity-lede">Administração da conta e configurações do LoadX.</p>
        </div>
      </header>
      {/* Seções escolhidas pela sidebar global; não criar um segundo menu. */}
      <SettingsSection id="settings-account" title="Conta e administração" hidden={activeSection !== "settings-account"}>
        <h3>Conta conectada</h3>
        <dl className="settings-profile">
          <div><dt>Nome</dt><dd>{user.name}</dd></div>
          <div><dt>E-mail</dt><dd>{user.email}</dd></div>
          <div><dt>Perfil</dt><dd>Administrador</dd></div>
        </dl>
        <p>Informações da sessão atual, somente para consulta.</p><Link className="settings-account-link" to="/account">Meu perfil, senha e sessões</Link>
        <ul className="settings-upcoming">
          {UPCOMING_ACCOUNT_SECTIONS.map((section) => (
            <li key={section.id}>
              <h3>{section.title}</h3>
              <p>{section.description}</p>
              <span className="settings-pending">Em preparação</span>
            </li>
          ))}
        </ul>
      </SettingsSection>
      <SettingsSection id="settings-company" title="Dados da empresa" hidden={activeSection !== "settings-company"}><CompanyProfileForm /></SettingsSection>
      <SettingsSection id="settings-integrations" title="Integrações e Saúde" hidden={activeSection !== "settings-integrations"}><IntegrationHealthPanel /></SettingsSection>
      <SettingsSection id="settings-logistics" title="Configurações do LoadX" hidden={activeSection !== "settings-logistics"}>
        <p>Esta seção reúne as configurações específicas do módulo logístico,
          separadas da administração da conta e dos dados da empresa.</p>
        <p>Não há configurações logísticas adicionais disponíveis nesta etapa.
          Cadastros e operações continuam nos respectivos módulos do menu.</p>
      </SettingsSection>
    </div>
  );
}
