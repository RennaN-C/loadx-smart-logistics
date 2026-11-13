import { OutboxPanel } from "../components/OutboxPanel";
import { AccessManagementPanel } from "../../users/components/AccessManagementPanel";
import { Link, useLocation } from "react-router-dom";
import { Icon } from "../../../components/Icon";
import { activeSettingsSection, SETTINGS_SECTIONS } from "../settingsSections";
import { useAuth } from "../../auth/hooks/useAuth";
import { CompanyProfileForm } from "../components/CompanyProfileForm";
import { IntegrationHealthPanel } from "../components/IntegrationHealthPanel";
import { AppearancePreferences } from "../../auth/components/AppearancePreferences";
import { NotificationPreferences } from "../../notifications/components/NotificationPreferences";
import { SettingsSection } from "../components/SettingsSection";
import "../../auth/pages/AccountPage.css";
import "./SettingsPage.css";

export function SettingsPage() {
  const { user } = useAuth();
  const { hash } = useLocation();
  const activeId = activeSettingsSection(hash);
  const accessManagement = activeId === "settings-users";
  if (!user) return null;

  return (
    <div className="entity-page settings-page">
      <header className="entity-header settings-header">
        <div>
          <p className="settings-eyebrow">Administração</p>
          <h1>{accessManagement ? "Gestão de usuários" : "Configurações"}</h1>
          <p className="entity-lede">
            {accessManagement ? "Gerencie usuários, perfis e permissões de acesso."
              : "Gerencie a identidade institucional, a saúde da plataforma e suas preferências."}
          </p>
        </div>
        <span className="settings-access"><Icon name="settings" size={16} />Acesso administrativo</span>
      </header>
      <nav className="section-navigation" aria-label="Seções de Configurações">
        {SETTINGS_SECTIONS.map((section) =>
          <Link key={section.id} to={`/settings#${section.id}`} aria-current={activeId === section.id ? "location" : undefined}>
            {section.label}
          </Link>,
        )}
      </nav>
      <div className="settings-content">
        {/* A empresa cadastrada identifica a instalação; não constitui um tenant SaaS. */}
        <SettingsSection id="settings-company" title="Dados da empresa"
          description="Identificação e contato institucionais deste ambiente. Não determina acesso nem isolamento de dados."
          hidden={activeId !== "settings-company"}>
          <CompanyProfileForm />
        </SettingsSection>
        <SettingsSection id="settings-users" title="Gestão de usuários" headingHidden hidden={!accessManagement}>
          {accessManagement ? <AccessManagementPanel /> : null}
        </SettingsSection>
        <SettingsSection id="settings-integrations" title="Integrações e Saúde"
          description="Diagnóstico real de disponibilidade, modos de operação e limites de cada serviço."
          hidden={activeId !== "settings-integrations"}>
          {activeId === "settings-integrations" ? <IntegrationHealthPanel /> : null}
        </SettingsSection>
        <SettingsSection id="settings-outbox" title="Fila de eventos" headingHidden hidden={activeId !== "settings-outbox"}>
          {activeId === "settings-outbox" ? <OutboxPanel /> : null}
        </SettingsSection>
        <SettingsSection id="settings-preferences" title="Preferências"
          description="Controles funcionais de aparência e categorias de notificações da sua conta."
          hidden={activeId !== "settings-preferences"}>
          {activeId === "settings-preferences" ? <>
            <div className="settings-preference-grid"><AppearancePreferences /><NotificationPreferences /></div>
            <p className="settings-operational-note">
              Estas preferências são pessoais. Para trocar senha, gerenciar MFA e sessões, utilize <Link to="/account">Meu perfil</Link>.
              Parâmetros de capacidade e planejamento permanecem nos próprios módulos operacionais.
            </p>
          </> : null}
        </SettingsSection>
      </div>
    </div>
  );
}
