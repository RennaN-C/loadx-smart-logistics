import type { ReactNode } from "react";

interface SettingsSectionProps {
  readonly id: string;
  readonly title: string;
  readonly hidden?: boolean;
  readonly children: ReactNode;
}

export function SettingsSection({ id, title, hidden, children }: SettingsSectionProps) {
  return (
    <section id={id} className="settings-section" aria-labelledby={`${id}-title`} hidden={hidden}>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}
