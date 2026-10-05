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
  /**
   * Problema deste campo. Substitui a dica enquanto existe: as duas juntas
   * empilham dois textos pequenos embaixo do campo e a pessoa lê o errado.
   *
   * Quem passa `error` também precisa espalhar `fieldErrorProps(id, error)`
   * (em `fieldErrorProps.ts`) no controle — é isso que liga o texto ao campo
   * para o leitor de tela.
   */
  readonly error?: string | null;
  readonly narrow?: boolean;
  readonly children: ReactNode;
}

export function FormField({ id, label, hint, tooltip, error, narrow, children }: FormFieldProps) {
  return (
    <div className={narrow ? "entity-form-field entity-form-field-narrow" : "entity-form-field"}>
      <span className="field-label-row">
        <label className="field-label" htmlFor={id}>
          {label}
        </label>
        {tooltip ? <Tooltip text={tooltip} label={`Sobre ${label.toLowerCase()}`} /> : null}
      </span>
      {children}
      {/* sem role="alert" de propósito: num envio com três campos errados, três
          alertas disputam o leitor de tela. O resumo em AlertBanner anuncia, e
          cada campo é lido quando recebe foco, via aria-describedby. */}
      {error ? (
        <p className="entity-form-error" id={`${id}-error`}>
          {error}
        </p>
      ) : null}
      {hint && !error ? <p className="entity-form-help">{hint}</p> : null}
    </div>
  );
}
