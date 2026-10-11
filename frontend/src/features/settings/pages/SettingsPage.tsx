import { Link, useLocation } from "react-router-dom";
import { Icon, type IconName } from "../../../components/Icon";
import { useAuth } from "../../auth/hooks/useAuth";
import { CompanyProfileForm } from "../components/CompanyProfileForm";
import { IntegrationHealthPanel } from "../components/IntegrationHealthPanel";
import { SettingsAccountPanel } from "../components/SettingsAccountPanel";
import { SettingsSection } from "../components/SettingsSection";
import "./SettingsPage.css";

const SECTIONS: readonly { id: string; title: string; label: string; icon: IconName }[] = [
  { id: "settings-account", title: "Conta e administração", label: "Conta", icon: "users" },
  { id: "settings-company", title: "Dados da empresa", label: "Empresa", icon: "orders" },
  { id: "settings-integrations", title: "Integrações e Saúde", label: "Integrações", icon: "gauge" },
  { id: "settings-logistics", title: "Configurações do LoadX", label: "Operação", icon: "settings" },
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
          {SECTIONS.map((section) => <Link key={section.id} to={`#${section.id}`} className="settings-nav-link" aria-label={section.title} aria-current={activeId === section.id ? "location" : undefined}>
            <Icon name={section.icon} size={18} /><span>{section.label}</span>
          </Link>)}
        </nav>
        <div className="settings-content">
          {/* Manter os painéis montados preserva o rascunho ao trocar de seção. */}
          <SettingsSection id="settings-account" title="Conta e administração" description="Informações da sessão e acesso às configurações pessoais." hidden={activeId !== "settings-account"}><SettingsAccountPanel user={user} /></SettingsSection>
          <SettingsSection id="settings-company" title="Dados da empresa" description="Identificação institucional, canais de contato e referência de marca." hidden={activeId !== "settings-company"}><CompanyProfileForm /></SettingsSection>
          <SettingsSection id="settings-integrations" title="Integrações e Saúde" description="Consulte o estado real dos serviços e os limites de cada integração." hidden={activeId !== "settings-integrations"}><IntegrationHealthPanel /></SettingsSection>
          <SettingsSection id="settings-logistics" title="Configurações do LoadX" description="Configurações próprias da operação, separadas dos dados da empresa." hidden={activeId !== "settings-logistics"}>
            <div className="settings-operational-links">
              <Link className="settings-operation-link" to="/fleet"><Icon name="truck" size={24} /><div><h3>Frota e disponibilidade</h3><p>Consulte veículos, motoristas e restrições da operação.</p><span>Consultar frota <Icon name="arrow-right" size={16} /></span></div></Link>
              <Link className="settings-operation-link" to="/planning"><Icon name="planning" size={24} /><div><h3>Planejamento de cargas</h3><p>Acesse os pedidos e os recursos do planejamento.</p><span>Ir para planejamento <Icon name="arrow-right" size={16} /></span></div></Link>
            </div>
            <p className="settings-operational-note">Os parâmetros operacionais são gerenciados nos respectivos módulos. Não há configurações logísticas adicionais disponíveis nesta etapa.</p>
          </SettingsSection>
        </div>
      </div>
    </div>
  );
}
