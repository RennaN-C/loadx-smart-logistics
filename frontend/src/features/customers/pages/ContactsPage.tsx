import { useAuth } from "../../auth/hooks/useAuth";
import { hasPermission } from "../../auth/permissions";
import { AlertBanner } from "../../../components/AlertBanner";
import { useSearchParams } from "react-router-dom";

import { Tabs, type TabItem } from "../../../components/Tabs";
import { DriverPanel } from "../../drivers/components/DriverPanel";
import { CustomerPanel } from "../components/CustomerPanel";
import "./ContactsPage.css";

type ContactTab = "customers" | "drivers";

const TABS: readonly TabItem<ContactTab>[] = [
  { id: "customers", label: "Clientes" },
  { id: "drivers", label: "Motoristas" },
];

/**
 * OC28 pede uma tela só para os dois cadastros. Cada aba é um painel que a sua
 * própria feature entrega — esta página só compõe. Por isso o import cruzado
 * para `drivers`: é composição de tela, não regra de negócio compartilhada.
 */
export function ContactsPage() {
  const { user } = useAuth();
  const tabs = TABS.filter((tab) => hasPermission(user, `loadx.${tab.id}.read`));
  const [params, setParams] = useSearchParams();
  const activeTab: ContactTab = params.get("tab") === "drivers" && tabs.some((tab) => tab.id === "drivers") ? "drivers" : tabs[0]?.id ?? "customers";
  function setActiveTab(tab: ContactTab) {
    const next = new URLSearchParams(params);
    next.set("tab", tab);
    next.delete("search");
    setParams(next);
  }

  if (!tabs.length) return <AlertBanner>Seu perfil não tem permissão para consultar estes cadastros.</AlertBanner>;
  const onlyCustomers = tabs.length === 1 && tabs[0]?.id === "customers";
  const onlyDrivers = tabs.length === 1 && tabs[0]?.id === "drivers";
  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>{onlyCustomers ? "Clientes" : onlyDrivers ? "Motoristas" : "Clientes e motoristas"}</h1>
          <p className="entity-lede">{onlyCustomers ? "Quem recebe a carga." : onlyDrivers ? "Quem leva a carga." : "Quem recebe a carga e quem leva."}</p>
        </div>
      </header>

      <Tabs items={tabs} active={activeTab} onChange={setActiveTab} label="Tipo de cadastro" />

      <div
        role="tabpanel"
        id={`panel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        className="contacts-panel"
      >
        {activeTab === "customers" ? <CustomerPanel /> : <DriverPanel />}
      </div>
    </div>
  );
}
