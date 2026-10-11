# App

Inicialização do React, providers globais, layout e rotas.

Não coloque telas completas nem regras de feature aqui. O App deve apenas montar a aplicação.

## Menu lateral

O menu fica numa barra à esquerda, fixa na rolagem. Vertical porque a lista cresce a cada
ocorrência e comporta agrupamento, que a barra no topo não comportava: os itens estão divididos
entre **Cadastros** (o que se cadastra uma vez) e **Operação** (o que se movimenta todo dia).

`NAV_GROUPS` declara os perfis que leem cada item, espelhando o `require_roles` do backend.
Esconder o link não substitui o backend, que continua barrando — evita só oferecer um caminho
que responderia 403. **Grupo que fica sem itens some junto com o título**, senão o conferente
veria "Cadastros" sobre lugar nenhum.

Abaixo de 900px a barra deita no topo e quebra em duas linhas: identidade e conta em cima, menu
na largura inteira embaixo, rolando na horizontal. Não vira gaveta — sem estado, sem botão e sem
precisar prender o foco. Espremido ao lado da conta, o menu tinha 130px de janela para 560px de
links; na linha inteira passa a mostrar 60% deles de saída num aparelho de 375px.

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
