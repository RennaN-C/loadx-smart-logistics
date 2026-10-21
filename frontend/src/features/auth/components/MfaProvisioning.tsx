import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";

/** The provisioning credential never leaves the browser or enters storage. */
export function MfaProvisioning({ uri }: { readonly uri: string }) {
  const [copyStatus, setCopyStatus] = useState("");
  const secret = new URL(uri).searchParams.get("secret") ?? "";
  async function copyKey() {
    try {
      await navigator.clipboard.writeText(secret);
      setCopyStatus("Chave copiada. Cole no seu autenticador.");
    } catch {
      setCopyStatus("Não foi possível copiar. Selecione a chave abaixo e copie manualmente.");
    }
  }
  return <section className="identity-enrollment" aria-label="Cadastro do autenticador">
    <p>No Google Authenticator, toque em + e escolha Escanear um código QR. Depois, informe os seis dígitos abaixo.</p>
    <div className="identity-qr"><QRCodeSVG value={uri} size={224} level="M" marginSize={4} title="QR Code para configurar o autenticador LoadX" /></div>
    <details className="identity-manual"><summary>Não consegue escanear? Use a chave manual</summary>
      <p>Escolha Inserir chave de configuração, nomeie a conta como LoadX e selecione Baseado no tempo.</p>
      <label className="identity-provision">Chave de configuração<input readOnly value={secret} onFocus={event => event.target.select()} /></label>
      <button type="button" className="btn-secondary" onClick={() => void copyKey()}>Copiar chave</button>
      <output className="identity-copy-status">{copyStatus}</output>
      <label className="identity-provision">URI de provisionamento<textarea readOnly value={uri} rows={4} /></label>
    </details>
    <p>Esta chave é secreta. Não compartilhe o QR Code nem capturas desta tela.</p>
  </section>;
}
