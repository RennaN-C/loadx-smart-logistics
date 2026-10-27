import { AssistantConversation, type Turn } from "./AssistantConversation";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
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
  const launcher = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const identity = `${user?.id}:${user?.role}:${user?.permissions?.join(",")}`;
  const enabled = user && ["ADMIN", "LOGISTICS_MANAGER", "CHECKER"].includes(user.role);
  useEffect(() => {
    request.current?.abort(); request.current = null;
    setOpen(false); setSelectedCustomer(null); setTurns([]); setDraft(""); setFailed(null); setWorking(false); setContext(routeContext(pathname));
    // Trocar de tela NÃO remove a conversa; somente trocar de usuário/perfil.
  }, [identity]);
  useEffect(() => {
    // Atualizar o contexto da tela sem remover perguntas, filtro de cliente ou rascunho.
    // Um diagnóstico de erro anterior não deve ser aplicado a outra aba.
    setContext((previous) => ({ ...routeContext(pathname), customerId: previous.customerId }));
  }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    panel.current?.querySelector<HTMLTextAreaElement>("textarea")?.focus();
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      const dialogs = document.querySelectorAll('[role="dialog"]');
      if (dialogs[dialogs.length - 1] !== panel.current) return;
      event.preventDefault();
      close();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (previousFocus?.isConnected) previousFocus.focus();
      else launcher.current?.focus();
    };
  }, [open]);
  useEffect(() => {
    const listener = (event: Event) => {
      request.current?.abort(); request.current = null;
      const detail = (event as CustomEvent<AssistantOpenContext>).detail ?? {};
      setContext(detail.diagnosticToken ? { diagnosticToken: detail.diagnosticToken } : { ...routeContext(pathname), planId: detail.planId ?? routeContext(pathname).planId, distributionId: detail.distributionId ?? routeContext(pathname).distributionId });
      setSelectedCustomer(null);
      setDraft(typeof detail.question === "string" ? detail.question.slice(0, 2000) : ""); setTurns([]); setFailed(null); setWorking(false); setOpen(true);
    };
    window.addEventListener("loadx:assistant", listener);
    return () => { window.removeEventListener("loadx:assistant", listener); };
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
    const history: ChatMessage[] = turns.slice(-4).flatMap((turn) => turn.reply ? [{ role: "user" as const, content: turn.question }, { role: "assistant" as const, content: turn.reply.answer.slice(0, 2000) }] : []);
    try {
      const reply = await askAssistant(question.trim(), history, context, controller.signal);
      if (!controller.signal.aborted && request.current === controller) {
        const planLink = reply.facts
          .filter((fact) => fact.name === "Análise do planejamento")
          .flatMap((fact) => fact.links ?? [])
          .map((link) => /^\/planning\/([0-9a-f-]{36})$/i.exec(link.href))
          .find((match) => match !== null);
        if (planLink) {
          // A referência veio de fato autorizado pelo backend; será revalidada
          // no servidor em cada pergunta, não inferida do histórico da IA.
          setContext((current) => ({ ...current, planId: planLink[1], distributionId: undefined }));
        } else if (reply.facts.some((fact) => fact.name === "Histórico de planejamentos")) {
          // Uma lista não seleciona plano; evita associar o próximo "esse" ao antigo.
          setContext((current) => ({ ...current, planId: routeContext(pathname).planId }));
        }
        setTurns((previous) => [...previous.slice(-19), {
          id: crypto.randomUUID(), question,
          reply: { ...reply, facts: reply.facts.map((fact) => ({ ...fact, clientKey: crypto.randomUUID() })) },
        }]);
        setDraft("");
      }
    } catch (error) {
      if (!controller.signal.aborted && request.current === controller) {
        setFailed(assistantErrorMessage(error));
      }
    } finally {
      if (request.current === controller) { request.current = null; setWorking(false); }
    }
  }
  function handleComposerKeyDown(event: import("react").KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    void send();
  }
  if (!enabled) return null;
  const sendLabel = working ? "Consultando…" : "Enviar pergunta";
  const submitLabel = failed && !working ? "Tentar novamente" : sendLabel;
  return <>
    <button ref={launcher} type="button" className="assistant-launch" aria-label="Conversar com Loxi" aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? titleId : undefined} onClick={() => open ? close() : setOpen(true)}>
      <Icon name="message-circle" size={23} /><span>Loxi</span>
    </button>
    {open ? createPortal(<div className="assistant-shell">
      <section ref={panel} className="assistant-panel" id={titleId} role="dialog" aria-modal="false" aria-labelledby={titleId + "-title"}>
        <header className="assistant-panel-header">
          <div><h2 id={titleId + "-title"}>Loxi <span className="assistant-title-caption">· Assistente LoadX</span></h2><p>Consultas, planejamentos e orientação operacional</p></div>
          <button type="button" className="assistant-close" aria-label="Minimizar assistente" title="Minimizar assistente" onClick={close}>×</button>
        </header>
        <div className="assistant-panel-body">
      <details className="assistant-privacy"><summary>Privacidade e limites</summary><p>Não compartilhe senhas ou documentos. O Loxi consulta somente informações autorizadas. Alterações exigem confirmação nas telas do LoadX.</p></details>
      <AssistantConversation turns={turns} onLink={close} onSelectCustomer={selectCustomer} working={working} />
      {working ? <output><span className="spinner" aria-hidden="true" /> Consultando informações autorizadas…</output> : null}
      {failed ? <AlertBanner>{failed}</AlertBanner> : null}
      {selectedCustomer ? <div className="assistant-filter"><span>Cliente: {selectedCustomer.label}</span><button type="button" className="btn-secondary" disabled={working} onClick={clearCustomer}>Limpar filtro de cliente</button></div> : null}
      <form onSubmit={(event: FormEvent) => { event.preventDefault(); void send(); }}>
        <div className="assistant-compose-header"><label htmlFor="assistant-message">Sua pergunta</label></div><textarea id="assistant-message" value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleComposerKeyDown} maxLength={2000} rows={1} disabled={working} title="Enter para enviar, Shift+Enter para nova linha" placeholder="Ex.: Quantos pedidos foram entregues?" />
        <div className="entity-form-actions"><button className="assistant-clear" type="button" disabled={working || turns.length === 0} onClick={() => { setTurns([]); setFailed(null); }}>Limpar conversa</button><button className="btn-primary assistant-submit" type="submit" aria-label={submitLabel} disabled={working || !draft.trim()}>{working ? "Consultando…" : "Enviar"}<Icon name="arrow-right" size={16} /></button></div>
      </form>
        </div>
      </section>
    </div>, document.body) : null}
  </>;
}
