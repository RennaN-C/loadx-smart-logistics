# Perfis e permissões — OC112

`CONFIRMADO`: Configurações → Perfis e permissões utiliza o submenu existente,
sem outra navegação. Painel só é montado na seção ativa e só consulta API para
ADMIN ativo. Não ADMIN continua bloqueado por RequireSettingsAdmin e pelo servidor.

Perfis fixos são consultáveis/protegidos. Perfis personalizados têm nome,
descrição, estado, seleção de grants reais agrupados e confirmação antes de
salvar. Estado inativo não é oferecido em uso; servidor revalida e trata conflito
concorrente pela versão. Não há exclusão ou botão decorativo.

OC86 acrescenta seleção paginada de perfil personalizado, preservando seleção
fora da página, papéis fixos, DRIVER e confirmação/revogação. Alteração envia o
UUID, nunca regras executáveis. Login/me provêm a projeção efetiva em memória.
Permissões não são persistidas em localStorage. Conta própria continua acessível.

A política de UI em auth/permissions.ts reflete grants do servidor, sem inferir
acesso CUSTOM a partir do gerente. Ausência de grants CUSTOM nega. As projeções
fixas preservam consumidores legados; API permanece a fonte de autorização.
Rotas, menus, ações, busca e consultas auxiliares respeitam a permissão do
recurso. Leitura/gestão são independentes; cadastro de perfil explica dependências.

Testes: componente/API/integração OC86, negação por perfil, reservadas, versão,
loading/erro/vazio, confirmação, paginação e projeção. Evidências Chromium reais
em docs/evidencias/oc112, com temas claro/escuro, sistema e teclado. Sem novas
dependências, MFA, recuperação ou integração CoreFlow.
