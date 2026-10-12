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

**Integração pendente:** a PR #201 trabalha o redesenho visual de Configurações
em branch separada. A PR #203 não incorpora esse redesign; reconciliar as duas
PRs antes de publicar uma versão combinada, evitando voltar a criar navegação
duplicada.
