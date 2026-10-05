import { FormField } from "./FormField";
import { fieldErrorProps } from "./fieldErrorProps";

export interface EntityNameFieldConfig {
  readonly id: string;
  readonly label: string;
  readonly placeholder: string;
}

interface EntityNameFieldProps {
  readonly config: EntityNameFieldConfig;
  readonly value: string;
  readonly error?: string;
  readonly onChange: (value: string) => void;
}

/** Campo de nome compartilhado pelos formulários de entidades. */
export function EntityNameField({ config, value, error, onChange }: EntityNameFieldProps) {
  return (
    <FormField id={config.id} label={config.label} error={error}>
      <input
        id={config.id}
        name="name"
        required
        maxLength={160}
        placeholder={config.placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...fieldErrorProps(config.id, error)}
      />
    </FormField>
  );
}
