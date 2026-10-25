import { useAppearance } from "../../../app/theme/useAppearance";

export function AppearancePreferences() {
  const { preference, setPreference } = useAppearance();
  return <section className="account-section" aria-labelledby="own-appearance">
    <h2 id="own-appearance">Aparência</h2>
    <p id="appearance-help">Escolha como o LoadX aparece neste navegador. No modo automático, o tema acompanha seu dispositivo.</p>
    <fieldset className="appearance-options" aria-describedby="appearance-help">
      <legend className="sr-only">Tema da interface</legend>
      {([
        ["light", "Claro", "Superfícies claras e detalhes em âmbar."],
        ["dark", "Escuro", "Azul profundo e detalhes em âmbar."],
        ["system", "Automático", "Seguir a aparência do sistema."],
      ] as const).map(([value, label, description]) => <label key={value} className="appearance-option" aria-label={label} htmlFor={`appearance-${value}`}>
        <input id={`appearance-${value}`} type="radio" name="appearance" aria-describedby={`appearance-${value}-description`} value={value} checked={preference === value} onChange={() => setPreference(value)} />
        <span><strong>{label}</strong><small id={`appearance-${value}-description`}>{description}</small></span>
      </label>)}
    </fieldset>
    <p className="appearance-note">Aplicação imediata. Preferência local, sem sincronização entre contas ou dispositivos.</p>
  </section>;
}
