/** Seções administrativas que executam ações reais. IDs legados viram aliases seguros. */
export const SETTINGS_SECTIONS = [
  { id: "settings-company", label: "Dados da empresa" },
  { id: "settings-users", label: "Gestão de usuários" },
  { id: "settings-integrations", label: "Integrações e Saúde" },
  { id: "settings-outbox", label: "Fila de eventos" },
  { id: "settings-preferences", label: "Preferências" },
] as const;

export type SettingsSectionId = (typeof SETTINGS_SECTIONS)[number]["id"];

export function activeSettingsSection(hash: string): SettingsSectionId {
  if (["#settings-profiles", "#settings-users-profiles"].includes(hash)) return "settings-users";
  if (["#settings-account", "#settings-logistics"].includes(hash)) return "settings-preferences";
  return SETTINGS_SECTIONS.find((section) => `#${section.id}` === hash)?.id ?? "settings-company";
}
