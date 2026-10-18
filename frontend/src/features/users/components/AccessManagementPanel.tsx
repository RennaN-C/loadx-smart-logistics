import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef, type KeyboardEvent } from "react";
import { ProfilesPanel } from "../../access-profiles/components/ProfilesPanel";
import { UserManagementPanel } from "./UserManagementPanel";
import "./UserManagement.css";

const TABS = [
  { id: "users", label: "Usuários", hash: "#settings-users" },
  { id: "profiles", label: "Perfis de acesso", hash: "#settings-users-profiles" },
] as const;

export function AccessManagementPanel() {
  const { hash } = useLocation();
  const navigate = useNavigate();
  const profiles = hash !== TABS[0].hash;
  const tabs = useRef<HTMLDivElement>(null);
  const focusProfileTab = useRef(false);
  useEffect(() => {
    if (hash === "#settings-profiles") navigate({ hash: TABS[1].hash }, { replace: true });
  }, [hash, navigate]);
  useEffect(() => {
    if (profiles && focusProfileTab.current) {
      focusProfileTab.current = false;
      tabs.current?.querySelector<HTMLButtonElement>("#access-tab-profiles")?.focus();
    }
  }, [profiles]);
  function keyDown(event: KeyboardEvent) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let index = Number(!profiles);
    if (event.key === "Home") index = 0;
    if (event.key === "End") index = 1;
    navigate({ hash: TABS[index].hash });
    tabs.current?.querySelectorAll<HTMLButtonElement>("button")[index]?.focus();
  }
  return <div className="access-management">
    <div className="access-tabs" role="tablist" tabIndex={-1} aria-label="Gestão de acessos" ref={tabs} onKeyDown={keyDown}>
      {TABS.map((tab, index) => <button key={tab.id} id={`access-tab-${tab.id}`} role="tab" type="button" aria-selected={profiles === Boolean(index)} aria-controls={`access-panel-${tab.id}`} tabIndex={profiles === Boolean(index) ? 0 : -1} onClick={() => navigate({ hash: tab.hash })}>{tab.label}</button>)}
    </div>
    <div id="access-panel-users" role="tabpanel" aria-labelledby="access-tab-users" hidden={profiles}>
      <UserManagementPanel active={!profiles} onManageProfiles={() => { focusProfileTab.current = true; navigate({ hash: TABS[1].hash }); }} />
    </div>
    <div id="access-panel-profiles" role="tabpanel" aria-labelledby="access-tab-profiles" hidden={!profiles}>
      <ProfilesPanel active={profiles} />
    </div>
  </div>;
}
