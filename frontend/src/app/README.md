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
