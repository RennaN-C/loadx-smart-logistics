import type { ReactNode } from "react";

interface FormFieldProps {
  /** Precisa bater com o id do controle passado em children, para o label funcionar. */
  readonly id: string;
  readonly label: string;
  readonly hint?: string;
  readonly narrow?: boolean;
  readonly children: ReactNode;
}

export function FormField({ id, label, hint, narrow, children }: FormFieldProps) {
  return (
    <div className={narrow ? "entity-form-field entity-form-field-narrow" : "entity-form-field"}>
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint ? <p className="entity-form-help">{hint}</p> : null}
    </div>
  );
}
