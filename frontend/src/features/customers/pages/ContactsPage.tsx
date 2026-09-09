import { useState } from "react";

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
  const [activeTab, setActiveTab] = useState<ContactTab>("customers");

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Clientes e motoristas</h1>
          <p className="entity-lede">Quem recebe a carga e quem leva.</p>
        </div>
      </header>

      <Tabs items={TABS} active={activeTab} onChange={setActiveTab} label="Tipo de cadastro" />

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
