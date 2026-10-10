# Configurações administrativas — OC85

`CONFIRMADO`: `/settings`, menu Administração → Configurações, somente ADMIN
ativo. RequireAuth conserva carregamento e redirecionamento de sessão ausente;
RequireSettingsAdmin nega acesso direto de LOGISTICS_MANAGER/CHECKER/DRIVER,
ator ausente ou inativo, sem montar a página protegida. 401 e falha de restauração
seguem AuthProvider/LoginPage existentes; 403 de perfil apresenta Acesso negado.
A OC85 preserva autenticação e RBAC gerais; OC91 adiciona seu contrato administrativo e tabela institucional.

`CONFIRMADO`: contexto somente leitura vindo de useAuth (/auth/me existente),
sem outra cópia de identidade, storage ou dados institucionais inventados.
SettingsSection compõe seções identificadas/rotuladas semanticamente; conta e
administração ficam separadas das configurações próprias do módulo LoadX.
Layout, navegação, alertas e tokens visuais existentes são reutilizados.

`PENDENTE DE DEFINIÇÃO`: funções de gestão de usuários OC86 e segurança da
conta OC92 são entradas informativas em preparação, sem
links/rotas falsas, formulários ou chamadas prematuras. Ao implementá-las,
adicionar conteúdo/rotas filhas sob a mesma guarda e manter um único item no
menu principal. Configurações logísticas permanecem no módulo; futuras funções
de conta podem ser ocultadas/delegadas sem alterar páginas operacionais.
CoreFlow, SSO, tenant e licenciamento não são implementados nem dependências.

`CONFIRMADO`: não persiste preferências críticas no navegador. Nenhum cadastro
institucional é chave de isolamento. Página responsiva, títulos hierárquicos,
regiões nomeadas, âncoras de navegação e foco visível, sem interação por ícone só.

## Dados da empresa — OC91

`CONFIRMADO`: Administração → Configurações → Dados da empresa, na mesma
rota `/settings` e guarda ADMIN. Consulta `GET /api/v1/company-profile`;
resposta inicial nula não cria cadastro. Edição explícita e substituição via
`PUT /api/v1/company-profile`, com salvar/cancelar, confirmação, loading,
repetição de consulta em falha e erros por campo associados ao controle.
Depois de F5 os dados são consultados novamente na API.

Nome empresarial e de exibição são obrigatórios. CNPJ numérico com dígitos
verificadores, telefone com DDD, e-mail e referência HTTPS são opcionais;
vazio limpa o campo. A referência não é carregada como imagem, não recebe
arquivos e não aceita credenciais na URL. Histórico mostra ator, data e
nomes dos campos alterados, sem valores. Outros perfis não consultam nem
editam o cadastro ou seus eventos. Não há tenant nem autenticação adicional.

Decisão e limites: [ADR-035](../../../../docs/decisions/ADR-035-configuracoes-institucionais-standalone.md).
