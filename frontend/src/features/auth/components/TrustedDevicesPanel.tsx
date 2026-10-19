import { useEffect, useState } from "react";
import { forgetCurrentDevice, listTrustedDevices, revokeAllTrustedDevices, revokeTrustedDevice, type TrustedDevices } from "../api/trustedDevicesApi";
import { accountError } from "./accountError";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export function TrustedDevicesPanel() {
  const [data, setData] = useState<TrustedDevices | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmAll, setConfirmAll] = useState(false);
  async function load() {
    setLoading(true); setError("");
    try { setData(await listTrustedDevices()); }
    catch (e) { setError(accountError(e)); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  async function revoke(action: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try {
      await action(); setConfirmAll(false);
      setNotice("Confiança removida. No próximo login, a verificação em duas etapas será exigida. A sessão atual permanece ativa.");
      await load();
    } catch (e) { setError(accountError(e)); }
    finally { setBusy(false); }
  }
  return <section className="identity-management identity-devices" aria-labelledby="trusted-devices-heading" aria-busy={loading || busy}>
    <header><h3 id="trusted-devices-heading">Dispositivos confiáveis</h3></header>
    <p>A confiança dispensa apenas o segundo fator neste navegador. A senha e os prazos normais da sessão continuam obrigatórios.</p>
    {loading && <output>Consultando dispositivos confiáveis…</output>}
    {error && <div><p role="alert">{error}</p><button type="button" className="btn-secondary" disabled={busy || loading} onClick={() => void load()}>Consultar novamente</button></div>}
    {notice && <output>{notice}</output>}
    {data && <>
      {!data.enabled && <p>Novas concessões e uso de confiança estão desabilitados neste ambiente. Você pode remover dispositivos registrados.</p>}
      {!data.items.length && !loading && <p>Nenhum dispositivo confiável ativo.</p>}
      <ul className="identity-device-list">{data.items.map(device => <li key={device.id}>
        <div><strong>{device.current ? "Este navegador" : `Dispositivo ${device.id.slice(0, 8)}`}</strong><dl>
          <div><dt>Registrado</dt><dd>{formatDate(device.created_at)}</dd></div>
          <div><dt>Último uso</dt><dd>{formatDate(device.last_used_at)}</dd></div>
          <div><dt>Expira em</dt><dd>{formatDate(device.expires_at)}</dd></div>
        </dl></div>
        <button type="button" className="btn-secondary" disabled={busy || loading} onClick={() => void revoke(() => device.current ? forgetCurrentDevice() : revokeTrustedDevice(device.id))} aria-label={`Remover ${device.current ? "este navegador" : `dispositivo ${device.id.slice(0, 8)}`}`}>{device.current ? "Esquecer este dispositivo" : "Remover dispositivo"}</button>
      </li>)}</ul>
      {data.items.length > 0 && <div className="identity-device-actions">
        {confirmAll ? <><p>Remover a confiança de todos os navegadores desta conta?</p><button type="button" className="btn-primary" disabled={busy || loading} onClick={() => void revoke(revokeAllTrustedDevices)}>Confirmar revogação de todos</button><button type="button" className="btn-secondary" disabled={busy} onClick={() => setConfirmAll(false)}>Cancelar</button></> : <button type="button" className="btn-secondary" disabled={busy || loading} onClick={() => setConfirmAll(true)}>Revogar todos os dispositivos</button>}
      </div>}
    </>}
  </section>;
}
