# Perfis e permissões — OC112

`CONFIRMADO`: Configurações → Gestão de usuários → Perfis de acesso reúne a administração
na aba interna, sem entrada paralela na sidebar. Painel só consulta API quando sua aba está ativa e para ADMIN ativo. Não ADMIN continua bloqueado por RequireSettingsAdmin e pelo servidor.

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

## UX unificada da OC112

`CONFIRMADO`: `#settings-users` abre Usuários; `#settings-users-profiles` abre
Perfis de acesso. O fragmento antigo `#settings-profiles` é normalizado com
replace, preservando links e o item ativo da sidebar. Anterior/próxima, F5 e
teclado (setas/Home/End) restauram a aba. Não existe uma segunda página de perfis.

`CONFIRMADO`: a listagem usa linhas compactas com nome, descrição, estado,
contagem de permissões/usuários, proteção e ações. Ver permissões abre consulta
somente leitura com módulos recolhidos. Rótulos vêm do catálogo da API; códigos
não aparecem na interface. Falha de catálogo tem repetição explícita, sem
substituir a resposta por permissões fictícias. Paginação continua no servidor.

`CONFIRMADO`: o editor mantém versão/confirmar/salvar/conflito, resumo de seleção
e grupos expansíveis. Ações protegidas ficam numa área recolhida com controles
desabilitados. Inativação em uso continua bloqueada pela UI e pelo backend.
Nenhum endpoint, regra de autorização, migration ou dependência foi alterado.
