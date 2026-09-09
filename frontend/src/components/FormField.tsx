import type { ReactNode } from "react";

import { Tooltip } from "./Tooltip";

interface FormFieldProps {
  /** Precisa bater com o id do controle passado em children, para o label funcionar. */
  readonly id: string;
  readonly label: string;
  /** Texto fixo abaixo do campo. Para o que se lê depois de preencher. */
  readonly hint?: string;
  /**
   * Dica sob demanda, num `i` ao lado do rótulo. Para o que se precisa saber
   * ANTES de digitar — formato, regra, o que o sistema faz com o valor —, sem
   * ocupar espaço permanente no formulário.
   */
  readonly tooltip?: string;
  readonly narrow?: boolean;
  readonly children: ReactNode;
}

export function FormField({ id, label, hint, tooltip, narrow, children }: FormFieldProps) {
  return (
    <div className={narrow ? "entity-form-field entity-form-field-narrow" : "entity-form-field"}>
      <span className="field-label-row">
        <label className="field-label" htmlFor={id}>
          {label}
        </label>
        {tooltip ? <Tooltip text={tooltip} label={`Sobre ${label.toLowerCase()}`} /> : null}
      </span>
      {children}
      {hint ? <p className="entity-form-help">{hint}</p> : null}
    </div>
  );
}
