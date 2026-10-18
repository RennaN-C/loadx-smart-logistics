import type { UserInput } from "../api/usersApi";
import { ROLE_LABELS } from "./userPresentation";
interface Props {
  readonly name: string;
  readonly draft: UserInput;
  readonly passwordChanged: boolean;
  readonly revoking: boolean;
  readonly ownAccount: boolean;
  readonly saving: boolean;
  readonly onConfirm: () => void;
  readonly onBack: () => void;
}
export function UserChangeConfirmation({ name, draft, passwordChanged, revoking, ownAccount, saving, onConfirm, onBack }: Props) {
  return <section aria-labelledby="user-confirm-title" className="user-confirmation">
    <h3 id="user-confirm-title">Confirmar alterações sensíveis</h3>
    <p id="user-confirm-summary">Confira as alterações na conta de <strong>{name}</strong> antes de continuar.</p>
    <dl><div><dt>Perfil</dt><dd>{ROLE_LABELS[draft.role]}{draft.customProfileId ? " — alteração do vínculo personalizado" : ""}</dd></div><div><dt>Estado</dt><dd>{draft.active ? "Ativo" : "Inativo"}</dd></div><div><dt>Vínculo</dt><dd>{draft.driverId ? "Motorista vinculado" : "Sem vínculo de motorista"}</dd></div><div><dt>Senha</dt><dd>{passwordChanged ? "Será redefinida" : "Preservada"}</dd></div></dl>
    {revoking ? <p>As sessões desta conta serão encerradas.{ownAccount ? " Esta é sua conta: será necessário entrar novamente." : ""}</p> : null}
    <div className="user-actions"><button id="user-confirm-action" aria-describedby="user-confirm-summary" className="btn-primary" type="button" disabled={saving} onClick={onConfirm}>{saving ? "Salvando…" : "Confirmar alterações"}</button><button className="btn-secondary" type="button" disabled={saving} onClick={onBack}>Voltar ao formulário</button></div>
  </section>;
}
