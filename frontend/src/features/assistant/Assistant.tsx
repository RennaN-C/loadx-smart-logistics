import { AssistantConversation, type Turn } from "./AssistantConversation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { Modal } from "../../components/Modal";
import { Icon } from "../../components/Icon";
import { AlertBanner } from "../../components/AlertBanner";
import { useAuth } from "../auth/hooks/useAuth";
import { askAssistant, assistantErrorMessage, type AssistantContext, type AssistantOpenContext, type ChatMessage, type CustomerChoice } from "./assistantApi";
import "./Assistant.css";

function routeContext(path: string): AssistantContext {
  const distribution = /^\/planning\/distributions\/([0-9a-f-]{36})$/i.exec(path);
  const plan = /^\/planning\/([0-9a-f-]{36})$/i.exec(path);
  if (distribution) return { distributionId: distribution[1] };
  return plan ? { planId: plan[1] } : {};
}
export function Assistant() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState<AssistantContext>({});
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerChoice | null>(null);
  const [working, setWorking] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const identity = `${user?.id}:${user?.role}:${user?.permissions?.join(",")}`;
  const enabled = user && ["ADMIN", "LOGISTICS_MANAGER", "CHECKER"].includes(user.role);
  useEffect(() => {
    request.current?.abort(); request.current = null;
    setOpen(false); setSelectedCustomer(null); setTurns([]); setDraft(""); setFailed(null); setWorking(false); setContext(routeContext(pathname));
  }, [identity, pathname]);
  useEffect(() => {
    const listener = (event: Event) => {
      request.current?.abort(); request.current = null;
      const detail = (event as CustomEvent<AssistantOpenContext>).detail ?? {};
      setContext({ ...routeContext(pathname), planId: detail.planId ?? routeContext(pathname).planId, distributionId: detail.distributionId ?? routeContext(pathname).distributionId });
      setSelectedCustomer(null);
      setDraft(typeof detail.question === "string" ? detail.question.slice(0, 2000) : ""); setTurns([]); setFailed(null); setWorking(false); setOpen(true);
    };
    window.addEventListener("loadx:assistant", listener);
    return () => { window.removeEventListener("loadx:assistant", listener); request.current?.abort(); };
  }, [pathname]);
  function selectCustomer(choice: CustomerChoice) {
    if (request.current) return;
    setSelectedCustomer(choice); setContext((current) => ({ ...current, customerId: choice.reference }));
    setDraft(turns.at(-1)?.question ?? "Consultar pedidos deste cliente");
  }
  function clearCustomer() { setSelectedCustomer(null); setContext((current) => ({ ...current, customerId: undefined })); }
  function close() { request.current?.abort(); request.current = null; setWorking(false); setOpen(false); }
  async function send(question = draft) {
    if (request.current || !question.trim() || working || question.length > 2000) return;
    const controller = new AbortController(); request.current = controller;
    setWorking(true); setFailed(null);
    const history: ChatMessage[] = turns.flatMap((turn) => turn.reply ? [{ role: "user" as const, content: turn.question }, { role: "assistant" as const, content: turn.reply.answer.slice(0, 2000) }] : []);
    try {
      const reply = await askAssistant(question.trim(), history, context, controller.signal);
      if (!controller.signal.aborted && request.current === controller) { setTurns((previous) => [...previous.slice(-3), { id: crypto.randomUUID(), question, reply: { ...reply, facts: reply.facts.map((fact) => ({ ...fact, clientKey: crypto.randomUUID() })) } }]); setDraft(""); }
    } catch (error) {
      if (!controller.signal.aborted && request.current === controller) {
        setFailed(assistantErrorMessage(error));
      }
    } finally {
      if (request.current === controller) { request.current = null; setWorking(false); }
    }
  }
  if (!enabled) return null;
  const sendLabel = working ? "Consultando…" : "Enviar pergunta";
  const submitLabel = failed && !working ? "Tentar novamente" : sendLabel;
  return <>
    <button type="button" className="btn-secondary assistant-launch" aria-label="Perguntar ao LoadX" aria-haspopup="dialog" onClick={() => setOpen(true)}><Icon name="search" size={16} /><span>Perguntar ao LoadX</span></button>
    {open ? createPortal(<div className="assistant-shell"><Modal title="Assistente LoadX" subtitle="Orientação e consultas autorizadas, sem alterar registros." onClose={close}>
      <button type="button" className="btn-secondary assistant-close" aria-label="Fechar assistente" onClick={close}><span aria-hidden="true">×</span></button>
      <p className="entity-form-help">Não informe senhas, documentos, endereços ou dados pessoais. A IA pode errar; confira os fatos do sistema.</p>
      <AssistantConversation turns={turns} onLink={close} onSelectCustomer={selectCustomer} working={working} />
      {working ? <output><span className="spinner" aria-hidden="true" /> Consultando informações autorizadas…</output> : null}
      {failed ? <AlertBanner>{failed}</AlertBanner> : null}
      <div className="assistant-suggestions" aria-label="Perguntas sugeridas">{(turns.at(-1)?.reply?.suggestions ?? ["Por que a carga não coube?", "Quantos pedidos foram entregues nos últimos 30 dias?", "O que faço agora?"]).map((suggestion) => <button type="button" className="btn-secondary" key={suggestion} disabled={working} onClick={() => setDraft(suggestion === "Tentar novamente" ? turns.at(-1)?.question ?? suggestion : suggestion)}>{suggestion}</button>)}</div>
      {selectedCustomer ? <div className="assistant-filter"><span>Cliente: {selectedCustomer.label}</span><button type="button" className="btn-secondary" disabled={working} onClick={clearCustomer}>Limpar filtro de cliente</button></div> : null}
      <form onSubmit={(event: FormEvent) => { event.preventDefault(); void send(); }}>
        <label htmlFor="assistant-message">Sua pergunta</label><textarea id="assistant-message" value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={2000} rows={2} disabled={working} placeholder="Pergunte sobre a operação ou os indicadores disponíveis" />
        <div className="entity-form-actions"><button className="btn-secondary" type="button" disabled={working || turns.length === 0} onClick={() => { setTurns([]); setFailed(null); }}>Limpar conversa</button><button className="btn-primary" type="submit" disabled={working || !draft.trim()}>{submitLabel}</button></div>
      </form>
    </Modal></div>, document.body) : null}
  </>;
}
