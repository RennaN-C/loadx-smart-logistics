import { Link } from "react-router-dom";
import { Avatar } from "../../../components/Avatar";
import { Icon } from "../../../components/Icon";
import type { AuthenticatedUser } from "../../auth/types";

export function SettingsAccountPanel({ user }: { readonly user: AuthenticatedUser }) {
  return <div className="settings-account-surface">
    <div className="settings-identity">
      <Avatar name={user.name} size={64} />
      <div><span className="settings-identity-label">Conta conectada</span><h3>{user.name}</h3><p>{user.email}</p></div>
      <span className="settings-role">Administrador</span>
    </div>
    <div className="settings-account-action">
      <Icon name="users" size={22} />
      <div><h3>Perfil e segurança</h3><p>Gerencie seus dados pessoais, altere a senha e consulte as sessões da sua conta.</p></div>
      <Link className="settings-account-link btn-secondary" to="/account">Meu perfil, senha e sessões <Icon name="arrow-right" size={16} /></Link>
    </div>
    <aside className="settings-upcoming" aria-labelledby="settings-users-shortcut-title">
      <div><h3 id="settings-users-shortcut-title">Gestão de usuários</h3></div>
      <p>Crie contas e gerencie perfis, senhas e vínculos de motorista.</p>
      <Link className="settings-account-link btn-secondary" to="/settings#settings-users">Gerenciar usuários <Icon name="arrow-right" size={16} /></Link>
    </aside>
  </div>;
}
