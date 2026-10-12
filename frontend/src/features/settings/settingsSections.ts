/** Seções reais de Configurações. Uma fonte para a sidebar e o conteúdo. */
export const SETTINGS_SECTIONS = [
  { id: "settings-account", label: "Conta e administração" },
  { id: "settings-company", label: "Dados da empresa" },
  { id: "settings-integrations", label: "Integrações e Saúde" },
  { id: "settings-logistics", label: "Configurações do LoadX" },
] as const;

export type SettingsSectionId = (typeof SETTINGS_SECTIONS)[number]["id"];

export function activeSettingsSection(hash: string): SettingsSectionId {
  return SETTINGS_SECTIONS.find((section) => `#${section.id}` === hash)?.id ?? "settings-account";
}
