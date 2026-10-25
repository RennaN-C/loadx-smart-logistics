export interface TabItem<T extends string> {
  readonly id: T;
  readonly label: string;
}

interface TabsProps<T extends string> {
  readonly items: readonly TabItem<T>[];
  readonly active: T;
  readonly onChange: (id: T) => void;
  /** Nome acessível da barra de abas, já que ela não tem título visível. */
  readonly label: string;
}

export function Tabs<T extends string>({ items, active, onChange, label }: TabsProps<T>) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          id={`tab-${item.id}`}
          aria-selected={item.id === active}
          aria-controls={`panel-${item.id}`}
          tabIndex={item.id === active ? 0 : -1}
          className="tab"
          onClick={() => onChange(item.id)}
          onKeyDown={(event) => {
            const index = items.findIndex((tab) => tab.id === item.id);
            const target = event.key === "ArrowRight" ? (index + 1) % items.length
              : event.key === "ArrowLeft" ? (index + items.length - 1) % items.length
                : event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : null;
            if (target === null) return;
            event.preventDefault();
            const next = items[target];
            onChange(next.id);
            const buttons = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
            buttons?.[target]?.focus();
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
