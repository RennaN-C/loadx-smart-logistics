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
          className="tab"
          onClick={() => onChange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
