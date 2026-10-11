import { Link } from "react-router-dom";
import { Avatar } from "../../../components/Avatar";
import { Icon } from "../../../components/Icon";
import type { AuthenticatedUser } from "../../auth/types";

export function SettingsAccountPanel({ user }: { readonly user: AuthenticatedUser }) {
  return <>
    <div className="settings-account-card">
      <div className="settings-card-heading"><Avatar name={user.name} size={44} /><div><h3>Conta conectada</h3><p>Informações da sessão atual, somente para consulta.</p></div><span className="settings-readonly">Somente leitura</span></div>
      <dl className="settings-profile">
        <div><dt>Nome</dt><dd>{user.name}</dd></div>
        <div><dt>E-mail</dt><dd>{user.email}</dd></div>
        <div><dt>Perfil</dt><dd>Administrador</dd></div>
      </dl>
      <div className="settings-account-action"><div><h3>Seu perfil e segurança</h3><p>Altere seus dados pessoais, senha e sessões na área da sua conta.</p></div><Link className="settings-account-link" to="/account"><Icon name="users" size={17} />Meu perfil, senha e sessões</Link></div>
    </div>
    <aside className="settings-upcoming" aria-labelledby="settings-users-title"><div><h3 id="settings-users-title">Gestão de usuários</h3><span className="settings-pending">Em preparação</span></div><p>Cadastro e gestão de acesso dos usuários do LoadX. Esta funcionalidade ainda não está disponível.</p></aside>
  </>;
}
