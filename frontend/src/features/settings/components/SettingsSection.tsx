import type { ReactNode } from "react";

interface SettingsSectionProps {
  readonly id: string;
  readonly title: string;
  readonly description?: string;
  readonly hidden?: boolean;
  readonly children: ReactNode;
}

export function SettingsSection({ id, title, description, hidden, children }: SettingsSectionProps) {
  return (
    <section id={id} className="settings-section" aria-labelledby={`${id}-title`} hidden={hidden}>
      <header className="settings-section-header"><h2 id={`${id}-title`}>{title}</h2>{description && <p>{description}</p>}</header>
      <div className="settings-section-body">{children}</div>
    </section>
  );
}
