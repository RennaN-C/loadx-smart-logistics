# Configurações administrativas — OC85

`CONFIRMADO`: `/settings`, menu Administração → Configurações, somente ADMIN
ativo. RequireAuth conserva carregamento e redirecionamento de sessão ausente;
RequireSettingsAdmin nega acesso direto de LOGISTICS_MANAGER/CHECKER/DRIVER,
ator ausente ou inativo, sem montar a página protegida. 401 e falha de restauração
seguem AuthProvider/LoginPage existentes; 403 de perfil apresenta Acesso negado.
Não altera contratos, autenticação, RBAC do backend nem schema PostgreSQL.

`CONFIRMADO`: contexto somente leitura vindo de useAuth (/auth/me existente),
sem outra cópia de identidade, storage ou dados institucionais inventados.
SettingsSection compõe seções identificadas/rotuladas semanticamente; conta e
administração ficam separadas das configurações próprias do módulo LoadX.
Layout, navegação, alertas e tokens visuais existentes são reutilizados.

`PENDENTE DE DEFINIÇÃO`: funções de gestão de usuários OC86, dados institucionais
OC91 e segurança da conta OC92 são entradas informativas em preparação, sem
links/rotas falsas, formulários ou chamadas prematuras. Ao implementá-las,
adicionar conteúdo/rotas filhas sob a mesma guarda e manter um único item no
menu principal. Configurações logísticas permanecem no módulo; futuras funções
de conta podem ser ocultadas/delegadas sem alterar páginas operacionais.
CoreFlow, SSO, tenant e licenciamento não são implementados nem dependências.

`CONFIRMADO`: não persiste preferências críticas no navegador. Nenhum cadastro
institucional é chave de isolamento. Página responsiva, títulos hierárquicos,
regiões nomeadas, âncoras de navegação e foco visível, sem interação por ícone só.
