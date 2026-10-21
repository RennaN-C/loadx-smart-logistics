export function RecoveryCodes({ codes, onDone }: { readonly codes: string[]; readonly onDone: () => void }) {
  return <section className="identity-codes" aria-labelledby="recovery-heading"><h2 id="recovery-heading">Guarde seus códigos de recuperação</h2><p>Salve em um local seguro, fora deste dispositivo. Cada código funciona uma única vez. Eles não serão mostrados novamente.</p><ul>{codes.map(code => <li key={code}><code>{code}</code></li>)}</ul><button className="btn-primary" onClick={onDone} type="button">Guardei os códigos, continuar</button></section>;
}
