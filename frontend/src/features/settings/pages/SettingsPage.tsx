import { useAuth } from "../../auth/hooks/useAuth";
import { CompanyProfileForm } from "../components/CompanyProfileForm";
import { SettingsSection } from "../components/SettingsSection";
import "./SettingsPage.css";

const UPCOMING_ACCOUNT_SECTIONS = [
  { id: "users", title: "Gestão de usuários", description: "Cadastro e gestão de acesso dos usuários do LoadX." },
  { id: "security", title: "Segurança da conta", description: "Gerenciamento de segurança da conta conectada." },
] as const;

export function SettingsPage() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div className="entity-page settings-page">
      <header className="entity-header">
        <div>
          <h1>Configurações</h1>
          <p className="entity-lede">Administração da conta e configurações do LoadX.</p>
        </div>
      </header>
      <nav className="settings-navigation" aria-label="Seções de configurações">
        <a href="#settings-account">Conta e administração</a>
        <a href="#settings-company">Dados da empresa</a>
        <a href="#settings-logistics">Configurações do LoadX</a>
      </nav>
      <SettingsSection id="settings-account" title="Conta e administração">
        <h3>Conta conectada</h3>
        <dl className="settings-profile">
          <div><dt>Nome</dt><dd>{user.name}</dd></div>
          <div><dt>E-mail</dt><dd>{user.email}</dd></div>
          <div><dt>Perfil</dt><dd>Administrador</dd></div>
        </dl>
        <p>Informações da sessão atual, somente para consulta.</p>
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
      <SettingsSection id="settings-company" title="Dados da empresa"><CompanyProfileForm /></SettingsSection>
      <SettingsSection id="settings-logistics" title="Configurações do LoadX">
        <p>Esta seção reúne as configurações específicas do módulo logístico,
          separadas da administração da conta e dos dados da empresa.</p>
        <p>Não há configurações logísticas adicionais disponíveis nesta etapa.
          Cadastros e operações continuam nos respectivos módulos do menu.</p>
      </SettingsSection>
    </div>
  );
}
