import { Link, useLocation } from "react-router-dom";
import { Icon, type IconName } from "../../../components/Icon";
import { useAuth } from "../../auth/hooks/useAuth";
import { CompanyProfileForm } from "../components/CompanyProfileForm";
import { IntegrationHealthPanel } from "../components/IntegrationHealthPanel";
import { SettingsAccountPanel } from "../components/SettingsAccountPanel";
import { SettingsSection } from "../components/SettingsSection";
import "./SettingsPage.css";

const SECTIONS: readonly { id: string; title: string; detail: string; icon: IconName }[] = [
  { id: "settings-account", title: "Conta e administração", detail: "Sua conta e acesso", icon: "users" },
  { id: "settings-company", title: "Dados da empresa", detail: "Identificação e contato", icon: "orders" },
  { id: "settings-integrations", title: "Integrações e Saúde", detail: "Serviços e conectividade", icon: "gauge" },
  { id: "settings-logistics", title: "Configurações do LoadX", detail: "Contexto operacional", icon: "settings" },
];

export function SettingsPage() {
  const { user } = useAuth();
  const { hash } = useLocation();
  const activeId = SECTIONS.find((section) => `#${section.id}` === hash)?.id ?? "settings-account";
  if (!user) return null;

  return (
    <div className="entity-page settings-page">
      <header className="entity-header settings-header">
        <div><p className="settings-eyebrow">Administração</p><h1>Configurações</h1>
          <p className="entity-lede">Gerencie os dados da empresa e acompanhe os serviços do LoadX.</p></div>
        <span className="settings-access"><Icon name="settings" size={16} />Acesso administrativo</span>
      </header>
      <div className="settings-workspace">
        <nav className="settings-navigation" aria-label="Seções de configurações">
          <p className="settings-nav-caption">Áreas de configuração</p>
          {SECTIONS.map((section) => <Link key={section.id} to={`#${section.id}`} className="settings-nav-link" aria-label={section.title} aria-current={activeId === section.id ? "location" : undefined}>
            <Icon name={section.icon} size={20} /><span>{section.title}<small aria-hidden="true">{section.detail}</small></span>
          </Link>)}
        </nav>
        <div className="settings-content">
          {/* Manter os painéis montados preserva o rascunho ao trocar de seção. */}
          <SettingsSection id="settings-account" title="Conta e administração" description="Informações da sessão e acesso às configurações pessoais." hidden={activeId !== "settings-account"}><SettingsAccountPanel user={user} /></SettingsSection>
          <SettingsSection id="settings-company" title="Dados da empresa" description="Identificação institucional, canais de contato e referência de marca." hidden={activeId !== "settings-company"}><CompanyProfileForm /></SettingsSection>
          <SettingsSection id="settings-integrations" title="Integrações e Saúde" description="Consulte o estado real dos serviços e os limites de cada integração." hidden={activeId !== "settings-integrations"}><IntegrationHealthPanel /></SettingsSection>
          <SettingsSection id="settings-logistics" title="Configurações do LoadX" description="Configurações próprias da operação, separadas dos dados da empresa." hidden={activeId !== "settings-logistics"}>
            <div className="settings-operational-note"><span className="settings-card-icon"><Icon name="truck" size={22} /></span><div>
              <h3>Parâmetros operacionais</h3><p>Não há configurações logísticas adicionais disponíveis nesta etapa. Cadastros e operações continuam nos respectivos módulos do menu.</p>
              <div className="settings-operational-links"><Link className="btn-secondary" to="/fleet">Consultar frota</Link><Link className="btn-secondary" to="/planning">Ir para planejamento</Link></div>
            </div></div>
          </SettingsSection>
        </div>
      </div>
    </div>
  );
}
