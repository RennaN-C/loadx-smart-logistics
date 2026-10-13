# Recuperação e continuidade — manutenção #208

`CONFIRMADO`: Chromium com frontend e API locais, PostgreSQL 16 e dados fictícios.
A matriz cobre Planos existentes, Novo planejamento, plano calculado e plano aprovado
com carregamento/viagem vinculados, em 375, 768, 1280×720 e 1920×1080 px,
nos temas claro/escuro: 32 capturas sem overflow externo. Imagens de erro/retry
e vazio complementam a matriz. Sidebar e acordeões da PR #207 foram preservados.

`CONFIRMADO`: cálculo explícito salvou um plano; navegação pelo menu para Produtos
e retorno à listagem reencontrou o registro, que reabriu após F5 e novo login.
A viagem vinculada abriu pelo plano sem oferecer criação duplicada. CHECKER
consultou somente aprovados e recuperou carregamento existente; DRIVER teve
acesso negado à área. Erro de rede apresentou retry; filtro REJECTED retornou
vazio real; página além do fim ofereceu retorno à primeira página.
Filtro por caminhão utiliza o UUID real ao clicar na placa; limpar, F5 e
navegação anterior/próxima do navegador foram conferidos contra a API.
Os resultados estruturados estão em [results.json](results.json) e [states.json](states.json).

`CONFIRMADO`: frontend completo: 741 testes/87 arquivos, ESLint, TypeScript e
build aprovados; npm audit sem vulnerabilidades. Resultados finais de backend: 2.176 testes aprovados, cobertura 94%, Ruff e Alembic aprovados.
Segurança e SonarCloud ficam na PR para corresponder ao SHA validado.

`PENDENTE DE DEFINIÇÃO`: salvar seleções anteriores ao cálculo exige contrato
próprio (usuário, autorização, validade, minimização de dados). Nesta entrega,
são memória React; não representam planos persistidos e não usam localStorage.
Central global de carregamentos/viagens/entregas continua na OC93 (#138);
liberação operacional de partes multi-caminhão continua sujeita à OC90.

## Capturas

| Largura / tema | Planos existentes | Novo planejamento | Calculado | Continuidade |
|---|---|---|---|---|
| 375 / dark | [Abrir](dark_375_plans.png) | [Abrir](dark_375_new.png) | [Abrir](dark_375_calculated.png) | [Abrir](dark_375_continuity.png) |
| 768 / dark | [Abrir](dark_768_plans.png) | [Abrir](dark_768_new.png) | [Abrir](dark_768_calculated.png) | [Abrir](dark_768_continuity.png) |
| 1280 / dark | [Abrir](dark_1280_plans.png) | [Abrir](dark_1280_new.png) | [Abrir](dark_1280_calculated.png) | [Abrir](dark_1280_continuity.png) |
| 1920 / dark | [Abrir](dark_1920_plans.png) | [Abrir](dark_1920_new.png) | [Abrir](dark_1920_calculated.png) | [Abrir](dark_1920_continuity.png) |
| 375 / light | [Abrir](light_375_plans.png) | [Abrir](light_375_new.png) | [Abrir](light_375_calculated.png) | [Abrir](light_375_continuity.png) |
| 768 / light | [Abrir](light_768_plans.png) | [Abrir](light_768_new.png) | [Abrir](light_768_calculated.png) | [Abrir](light_768_continuity.png) |
| 1280 / light | [Abrir](light_1280_plans.png) | [Abrir](light_1280_new.png) | [Abrir](light_1280_calculated.png) | [Abrir](light_1280_continuity.png) |
| 1920 / light | [Abrir](light_1920_plans.png) | [Abrir](light_1920_new.png) | [Abrir](light_1920_calculated.png) | [Abrir](light_1920_continuity.png) |

[Erro e nova tentativa](error_retry.png) · [Consulta vazia](empty.png)

## Reproduzir

1. Entrar como ADMIN ou LOGISTICS_MANAGER e abrir Planejamento de carga.
2. Em Novo planejamento, escolher caminhão/pedidos READY e calcular (até 200 volumes físicos).
3. Visitar Produtos pelo menu, voltar a Planejamento e abrir o registro na listagem.
4. Atualizar a página, sair/entrar novamente e consultar a mesma carga.
5. Filtrar situação/ordenar/paginar; abrir um plano aprovado com vínculos reais.
6. Conferir acesso de CHECKER e bloqueio de DRIVER; simular falha GET e tentar novamente.
7. Executar lint/build/testes frontend e Ruff/Alembic/Pytest com PostgreSQL 16 dedicado.
