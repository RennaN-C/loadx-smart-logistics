# OC103 — evidências de integração e interface

`CONFIRMADO`: validação em Chromium headless instalado no ambiente, com API real,
PostgreSQL 16 isolado e dados exclusivamente fictícios. Sem mocks de notificações
na aplicação ou registros de localStorage. Migration oficial aplicada por Alembic.
Não houve acesso/modificação de ambientes compartilhados ou deploy.

## Capturas

Capturas realizadas durante a inspeção, antes das ações de leitura em lote. Os
contadores refletem cada instante real do cenário; não foram editados nas imagens.
Há 28 PNGs: três superfícies × quatro larguras × dois temas, duas capturas adicionais
da lista no celular e estados reais de vazio/erro.

| Largura | Central (claro / escuro) | Dropdown (claro / escuro) | Preferências (claro / escuro) |
|---|---|---|---|
| 375 | [Claro](central-light-375.png) / [Escuro](central-dark-375.png) | [Claro](dropdown-light-375.png) / [Escuro](dropdown-dark-375.png) | [Claro](preferencias-light-375.png) / [Escuro](preferencias-dark-375.png) |
| 768 | [Claro](central-light-768.png) / [Escuro](central-dark-768.png) | [Claro](dropdown-light-768.png) / [Escuro](dropdown-dark-768.png) | [Claro](preferencias-light-768.png) / [Escuro](preferencias-dark-768.png) |
| 1280 | [Claro](central-light-1280.png) / [Escuro](central-dark-1280.png) | [Claro](dropdown-light-1280.png) / [Escuro](dropdown-dark-1280.png) | [Claro](preferencias-light-1280.png) / [Escuro](preferencias-dark-1280.png) |
| 1920 | [Claro](central-light-1920.png) / [Escuro](central-dark-1920.png) | [Claro](dropdown-light-1920.png) / [Escuro](dropdown-dark-1920.png) | [Claro](preferencias-light-1920.png) / [Escuro](preferencias-dark-1920.png) |

Lista no celular: [claro](central-lista-light-375.png) / [escuro](central-lista-dark-375.png).
Estados: [não lidas vazias após leitura real](vazio-light-1280.png) e
[falha real de transporte com retry](erro-dark-375.png). O bloqueio de transporte
foi removido e a recuperação confirmada; nenhum dado falso foi retornado pela API.

[validacao-visual.json](validacao-visual.json) registra dimensões, ausência de overflow,
rodapé do dropdown visível em todas as larguras, navegação à seção de preferências,
Escape/foco e mudança do sistema claro/escuro com preferência Automático. As imagens
foram revisadas, além da medição: contraste, tipografia, espaçamento e controles.

## Fluxo com persistência real

[validacao-fluxo.json](validacao-fluxo.json) registra:

1. Central com 9 fatos reais do cenário fictício; leitura individual reduz contador
   de 6 para 5, sem alterar outra caixa.
2. F5 mantém a leitura e contador; sair para Produtos e voltar pelo sino encontra
   os mesmos registros persistidos e mantém 5 não lidas.
3. Abrir operação navega à viagem existente; contagem de viagens permanece 1.
4. Link Preferências abre a seção correta. Tecla Espaço altera checkbox nativo;
   salvar/F5 mantém a preferência; segurança continua marcada e desabilitada.
   A preferência operacional foi reativada pela interface ao final do teste.
5. Árvore de acessibilidade não possui controle interativo visível sem nome.
6. Marcar todas reduz contador a zero. Filtro de não lidas mostra vazio real;
   falha de transporte mostra erro e nova tentativa recupera a consulta.

`CONFIRMADO`: testes Vitest adicionais cobrem retorno do foco após leitura,
Escape, erro sem sucesso fictício, filtros na URL, contador/lista sincronizados e
segurança obrigatória. O JSON não contém cookies, credenciais ou mensagens privadas.

## Validações técnicas

- PostgreSQL 16: **2.531 testes backend aprovados**, cobertura Pytest **95%**.
- Frontend: **925 testes / 105 arquivos aprovados**, ESLint, TypeScript/build,
  budget do bundle e npm audit (**0 vulnerabilidades**) aprovados.
- Ruff check/format; Alembic heads/current/upgrade/check/downgrade/upgrade aprovados
  em banco de migration novo e isolado, head único **20261020_0026**.
- CI/Segurança/Trivy/Sonar: resultados vinculados à [PR #228](https://github.com/RennaN-C/loadx-smart-logistics/pull/228).
  A análise automática do Sonar não importa a cobertura Pytest; 95% é a medição
  da suíte backend, não uma cobertura frontend ou do relatório automático Sonar.

## Limites

`CONFIRMADO`: somente eventos aprovados da OC84; sem alertas administrativos,
documentais ou de manutenção fictícios. Política de categorias futuras em ADR-042.
`RISCO IDENTIFICADO`: backfill usa autorização no corte; coordenar migration e
atualização dos escritores antes de implantar. Downgrade com leitura/destinatários/
preferências é recusado. Recuperação de canal e retries seguem na OC109.
