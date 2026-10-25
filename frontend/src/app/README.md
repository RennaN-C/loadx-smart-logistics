# App

Inicialização do React, providers globais, layout e rotas.

Não coloque telas completas nem regras de feature aqui. O App deve apenas montar a aplicação.

## Menu lateral

O menu fica numa barra à esquerda, fixa na rolagem. Vertical porque a lista cresce a cada
ocorrência e comporta agrupamento, que a barra no topo não comportava: os itens estão divididos
entre **Cadastros** (o que se cadastra uma vez) e **Operação** (o que se movimenta todo dia).

`NAV_GROUPS` declara os perfis que leem cada item, espelhando o `require_roles` do backend.
Esconder o link não substitui o backend, que continua barrando — evita só oferecer um caminho
que responderia 403. Na OC112, o rótulo de Clientes/Motoristas reflete apenas
os cadastros consultáveis; Relatórios e indicadores exige ambos os grants
`loadx.reports.read` e `loadx.orders.read`, pois a página consulta pedidos. **Grupo que fica sem itens some junto com o título**, senão o conferente
veria "Cadastros" sobre lugar nenhum.

Até 900px, o menu global é uma gaveta sobreposta, acionada pela barra compacta.
Acima de 900px, a mesma sidebar é recolhível para um trilho de ícones.

## Configurações — OC85

`CONFIRMADO`: ADMIN vê Administração → Configurações. `/settings` reutiliza
RequireAuth/AppLayout e monta SettingsPage sob RequireSettingsAdmin; demais
perfis recebem Acesso negado ao digitar a URL, sem conteúdo administrativo.
Não muda os itens/permissões operacionais existentes. Seções de conta e de
logística ficam na feature settings; OC86/91/92 não recebem rotas prematuras.


## Navegação recolhível (manutenção #202)

`CONFIRMADO`: em telas acima de 900 px, o botão da sidebar alterna entre
menu completo (236 px) e trilho compacto (80 px), mantendo ícones clicáveis,
nomes acessíveis e indicação de item ativo. A preferência usa armazenamento
local quando disponível e não altera RBAC nem rotas.

`CONFIRMADO`: até 900 px, a navegação fica sob um botão no cabeçalho e abre
em gaveta sobreposta, sem barra horizontal de links. Pode fechar com botão,
clique fora, Escape ou ao navegar. Enquanto aberta, a rolagem do fundo
fica suspensa e o foco retorna ao botão ao fechar. Movimentos reduzidos
são respeitados.

`PENDENTE DE VALIDAÇÃO MANUAL`: verificar a transição entre 900/901 px e
larguras 375, 768, 1280 e 1920 px no navegador, em temas claro/escuro,
incluindo textos longos, rolagem vertical da gaveta e modal aberto.

## Subseções de Configurações — manutenção #202 / PR #203

`CONFIRMADO`: Configurações é um item exclusivo de ADMIN e expande na **mesma**
sidebar global as quatro subseções (Conta e administração, Dados da empresa,
Integrações e Saúde, Configurações do LoadX). Não há segunda sidebar nem abas
horizontais na área de conteúdo. O painel central mostra somente a seção ativa,
sem desmontar as outras e perder um rascunho em andamento.

A seleção usa `/settings#settings-account`, `#settings-company`,
`#settings-integrations` ou `#settings-logistics`; URL sem hash ou
desconhecida seleciona Conta e administração. Links diretos e histórico
continuam disponíveis. A sidebar compacta abre ao selecionar Configurações.
No drawer mobile, tocar em Configurações expande suas opções sem fechar a gaveta;
tocar em uma subseção navega e fecha a gaveta.

A proteção de backend/frontend permanece ADMIN. O submenu não implementa
gestão de usuários, parâmetros inexistentes ou novos contratos HTTP.

`CONFIRMADO`: as PRs #201, #203 e #205 já estão integradas na base da manutenção
#206. A consolidação preserva as subseções de Configurações na sidebar global.

## Acordeões da sidebar — manutenção PR #203

`CONFIRMADO`: **Cadastros** e **Operação** possuem mais de um destino e agora
são grupos recolhíveis por botões nativos (`aria-expanded` e `aria-controls`).
Um clique oculta os links, outro clique volta a mostrá-los, sem trocar a página
ativa. Os grupos funcionam independentemente, têm estado visual e foco visível,
e nunca oferecem rotas que o perfil não pode acessar. Grupos com apenas um
destino (Início, Minha conta) não criam acordeões desnecessários.

**Configurações** mantém as quatro subseções na sidebar global. Clicar no item
pai na área já aberta recolhe o submenu; clicar novamente expande, preservando
o conteúdo e o fragmento atuais. Na sidebar compacta, os grupos mostram botões
com ícones acessíveis; selecionar um grupo expande a barra. No mobile, o drawer
permanece aberto durante abertura/fechamento de grupos e fecha ao escolher uma
rota final. Recarregar diretamente `/settings#settings-company` continua
selecionando a subseção correta.

Nenhuma alteração em endpoint, regras de autorização, schema ou permissões.

## Consolidação — manutenção #206

`CONFIRMADO`: navegação global Visão geral; Cadastros (Caminhões e frota,
Produtos, Clientes e motoristas); Operação (Pedidos, Planejamento de carga,
Relatórios e indicadores, Auditoria); Minha conta; Configurações. Acordeões,
sidebar compacta, drawer mobile, submenus e RBAC da PR #203 são preservados.

`CONFIRMADO`: aliases `/operations` → `/` (ADMIN/LOGISTICS_MANAGER) e `/fleet` →
`/trucks?tab=availability` (ADMIN/LOGISTICS_MANAGER/CHECKER). A guarda evita montar
componentes e consultas dos perfis negados, sem substituir autorização backend.

`RISCO IDENTIFICADO`: OC86 em desenvolvimento também altera AppLayout e testes
de Configurações; reconciliar os rótulos/links do menu ao integrar aquela branch.
Nenhum código de gestão de usuários/autenticação ou evidências OC81 foi remodelado.

## Grupos fechados por padrão — refinamento UX #206

`CONFIRMADO`: os grupos com múltiplas opções **Cadastros** e **Operação** iniciam fechados a cada montagem do menu; o usuário expande/recolhe pelo clique, inclusive no drawer mobile. O item ativo e a página atual não são alterados ao alternar o acordeão. A sidebar inteira mantém sua preferência independente de largura compacta. O submenu administrativo continua associado à rota de Configurações, preservando a seleção ativa e a navegação direta.

A continuidade de planos e viagens entre telas é uma lacuna funcional independente, rastreada pela Issue #208; não deve ser contornada com rascunho simulado ou plano criado automaticamente.

## Apresentação e navegação — revisão de 24/10/2026

`CONFIRMADO`: Controle reúne Relatórios, Auditoria e Notificações, preservando
as guardas específicas. A central de notificações também fica acessível no menu
para contas autenticadas. Os destinos começam expandidos; acordeões, trilho e
gaveta continuam operacionais. A sidebar permite rolagem própria para que todas
as subseções administrativas sejam alcançáveis em janelas baixas.

`CONFIRMADO`: tokens, tipografia de interface, foco, cabeçalhos e ações seguem
a composição azul/âmbar das referências, com equivalente claro. Não foram
adicionados endpoints, permissões ou dados de demonstração ao produto.

## Navegação padronizada — solicitação de 25/10/2026

`CONFIRMADO`: Configurações passa a ser um destino simples da sidebar, assim
como as demais áreas. Foram removidos o submenu e seu estado de expansão.
Selecionar Configurações fecha a gaveta móvel imediatamente e preserva o trilho
compacto. Suas seções usam navegação horizontal no conteúdo, mantendo os mesmos
fragmentos de URL e o controle ADMIN. Este comportamento substitui a apresentação
em submenu descrita nas seções históricas acima.

`CONFIRMADO`: `.section-navigation` padroniza frota, planejamento e configurações.
Gráficos, cabeçalhos e controles têm transições discretas; movimentos novos são
desativados com `prefers-reduced-motion: reduce`.
