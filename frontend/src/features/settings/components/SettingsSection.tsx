import type { ReactNode } from "react";

interface SettingsSectionProps {
  readonly id: string;
  readonly title: string;
  readonly children: ReactNode;
}

export function SettingsSection({ id, title, children }: SettingsSectionProps) {
  return (
    <section id={id} className="settings-section" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}
