# Riscos, pendências e decisões necessárias

Este documento concentra pontos que ainda precisam de validação da equipe. Não use itens daqui como decisão aprovada enquanto estiverem marcados como pendência, suposição ou risco.

## Decisões já confirmadas

- `CONFIRMADO`: arquitetura de monólito modular, conforme `ADR-001`.
- `CONFIRMADO`: unidades em centímetros, quilogramas e coordenadas `x/y/z`, conforme `ADR-002`.
- `CONFIRMADO`: IA como apoio, não como validadora física, conforme `ADR-003`.
- `CONFIRMADO`: endpoints públicos, matriz RBAC e bootstrap do primeiro administrador, conforme `ADR-004`.
- `CONFIRMADO`: transições, bloqueios de edição e histórico atômico de pedidos
  seguem D04, D05 e `ADR-015`.
- `CONFIRMADO`: campos decimais públicos usam exclusivamente número JSON, com
  `Decimal` preservado no domínio e precisão limitada conforme D06 e `ADR-016`.
- `CONFIRMADO`: D12 e `ADR-017` definem resumos sem dados pessoais
  desnecessários, paginação 1-based limitada a 100 registros e ordenação
  cronológica determinística para todas as coleções atuais.
- `CONFIRMADO`: D11 e `ADR-018` mantêm `/health` como liveness e definem
  `/ready` com PostgreSQL, Alembic head, orçamento de 2 segundos e resposta
  pública sem detalhes internos.
- `CONFIRMADO`: a OC58 implementa D11, integra `/ready` ao healthcheck do
  container backend e cobre banco disponível, indisponível e revisão divergente.
- `CONFIRMADO`: a OC59 aplica D12 no banco e na API de usuários, clientes,
  motoristas, pedidos, caminhões e produtos; o frontend de caminhões consome o
  envelope e permite navegar pelas páginas.
- `CONFIRMADO`: a OC60 implementa D18 com Argon2id, política de senha, limitação
  de login por conta e IP, sessões opacas revogáveis, cookie HttpOnly, proteção
  de Origin/CSRF, logout, revogação por mudanças sensíveis e frontend sem
  credenciais no Web Storage.
- `CONFIRMADO`: a OC61 implementa a referência de produção do `ADR-021` com
  Caddy/TLS, proxy confiável explícito, segredos montados, papéis PostgreSQL
  segregados e eventos estruturados para integração com alertas.
- `CONFIRMADO`: D07 a D10, D21 e `ADR-022` definem o ciclo restrito de viagens
  e entregas, finalização somente com todas as entregas concluídas, bloqueio
  fechado sem carregamento finalizado, catálogo auditável fechado e vínculo
  único `users.driver_id`.
- `CONFIRMADO`: as migrations `20260825_0009` e `20260825_0010` e seus models
  materializam ocorrências e carregamento. Uma sessão `FINISHED` do mesmo plano
  libera o início da viagem; ausência ou divergência continua falhando fechado.
- `CONFIRMADO`: a OC40 envia notificações automáticas mock após início efetivo
  de viagem e registro de ocorrência, sempre depois do commit e em modo
  best-effort.
- `CONFIRMADO`: fotos opcionais de ocorrência usam referência controlada
  `mock://occurrences/<identificador>`; storage real permanece futuro.
- `CONFIRMADO`: volumes individuais são expandidos de `order_items.quantity`, usam `volume_index` iniciado em `1` e são persistidos em `load_plan_items`, sem tabela `volumes`, conforme `ADR-005`.
- `CONFIRMADO`: volumes usam a ordem total determinística de volume, peso, empilhamento, fragilidade, entrega e identidade, conforme `ADR-006`.
- `CONFIRMADO`: rotações usam seis permutações ortogonais priorizadas, deduplicam simetrias e respeitam bloqueio por produto, conforme `ADR-007`.
- `CONFIRMADO`: o posicionamento usa pontos candidatos estáveis, ordem `(y, z, x, rotation_rank)` e first-fit com política física obrigatória, conforme `ADR-008`.
- `CONFIRMADO`: colisão AABB exige sobreposição positiva nos três eixos, permite contato e usa tolerância zero, conforme `ADR-009`.
- `CONFIRMADO`: apoio exige cobertura integral pela união exata dos contatos e aplica empilhamento e fragilidade a toda a cadeia de carga, conforme `ADR-010`.
- `CONFIRMADO`: engine, porta, profundidade e sequência topológica seguem a
  `ADR-013`.
- `CONFIRMADO`: snapshots, estados, aprovação e recálculo imutável seguem a
  `ADR-014`.
- `CONFIRMADO`: D17 fecha a OC21 com comparação de 2 a 10 caminhões, preflight
  integral, limite de 200 volumes, resposta não ranqueada e nenhuma persistência.
- `CONFIRMADO`: D22 fecha a OC22 com explicação de plano persistido, contexto sem
  dados pessoais, port e provider fake, timeout de 5 segundos por padrão, fallback
  determinístico e RBAC por estado do plano.
- `CONFIRMADO`: tecnologias oficiais descritas em `README.md` e `docs/02-arquitetura.md`.
- `CONFIRMADO`: nomes técnicos em inglês.
- `CONFIRMADO`: documentação oficial dentro da estrutura existente de `docs`.
- `CONFIRMADO`: Alembic configurado em `backend/alembic.ini` e `backend/migrations/env.py`.
- `CONFIRMADO`: migration inicial `20260729_0001` cria `users`, `customers`, `drivers`, `trucks` e `products`.
- `CONFIRMADO`: migration `20260730_0002` cria `orders` e `order_items`.
- `CONFIRMADO`: migration `20260730_0003` cria `status_history`.
- `CONFIRMADO`: migration `20260804_0004` cria as três tabelas de planejamento.
- `CONFIRMADO`: D18 e `ADR-020` substituem JWT por sessão opaca em cookie,
  mantêm login e `/auth/me`, adicionam logout, removem `/auth/register` e
  restringem criação de usuários a `ADMIN` após bootstrap local.
- `CONFIRMADO`: a `OC51-I` auditou a matriz completa de autorização e a fronteira pública de todos os endpoints atualmente implementados.
- `CONFIRMADO`: a `OC53` executa os testes de integração em PostgreSQL 16
  exclusivo, aplica migrations Alembic do banco vazio, exercita downgrade mínimo
  e isola cada cenário em transação externa.
- `CONFIRMADO`: a `OC55` centralizou fixtures, encerra clients, sessions e engines
  e deixou toda a base Python conforme Ruff.
- `CONFIRMADO`: o PR #23 implementa a integração contínua em
  `.github/workflows/ci.yml` para pull requests e pushes em `desenvolvimento` e
  `main`. Os jobs independentes `Backend` e `Frontend` e o check `SonarCloud`
  passaram integralmente no PR.
- `CONFIRMADO`: a CI do backend usa Python 3.12, PostgreSQL 16, Ruff, validação
  de formatação, Alembic e Pytest com cobertura. As dependências continuam
  separadas em runtime (`requirements.txt`) e desenvolvimento
  (`requirements-dev.txt`); a CI instala `requirements-dev.lock.txt`, com hashes e
  `--require-hashes`.
- `CONFIRMADO`: a CI do frontend usa o Node definido em `.nvmrc`, instala com
  `npm ci --ignore-scripts` e executa auditoria npm, ESLint, Vitest e build.
- `CONFIRMADO`: o workflow também constrói a imagem backend e executa Trivy
  para vulnerabilidades altas/críticas com correção disponível.
- `CONFIRMADO`: o ruleset de `main` exige os checks `Backend`, `Frontend` e
  `SonarCloud` e pelo menos uma aprovação antes do merge.
- `CONFIRMADO`: `ADR-019` define inicialização segura em produção, migrations
  automáticas antes do backend, processos de aplicação sem privilégio e portas
  locais restritas a loopback.
- `CONFIRMADO`: a auditoria de 2026-08-07 removeu a dependência transitiva
  vulnerável do `python-jose`, atualizou Router/Vite/Vitest e terminou com zero
  achados em `pip-audit`, `npm audit` e Bandit.

## Decisões necessárias

- `DECISÃO NECESSÁRIA`: definir formato final de relatório PDF e se haverá envio por e-mail/WhatsApp no MVP.

## Pendências técnicas

- `PENDENTE DE DEFINIÇÃO`: contrato e filtros de uma eventual consulta protegida
  de histórico; D10 fechou as entidades em `ORDER`, `LOAD_PLAN`, `TRIP` e
  `DELIVERY`, mas não aprovou endpoint na OC09.
- `PENDENTE DE DEFINIÇÃO`: coletor, retenção, destino e SLA dos logs e alertas;
  o backend já emite eventos JSON no logger `loadx.security` e marca casos que
  exigem alerta com `alert=true`.
- `PENDENTE DE DEFINIÇÃO`: recuperação de senha e MFA para `ADMIN` e
  `LOGISTICS_MANAGER` precisam de contrato de cadastro, recuperação, códigos de
  contingência, dispositivo perdido e bootstrap sem bloqueio administrativo.
- `PENDENTE DE DEFINIÇÃO`: qualquer CDN, balanceador ou proxy adicional à frente
  do Caddy exige nova definição da cadeia confiável. A referência atual aceita
  `X-Forwarded-*` no Uvicorn somente do IP privado fixo do Caddy.
- `PENDENTE DE DEFINIÇÃO`: escolher e configurar os provedores reais de cofre,
  PostgreSQL e alertas. O repositório já aceita segredos por arquivo, separa as
  URLs de migration/aplicação e fornece o SQL de menor privilégio.
- `PENDENTE DE DEFINIÇÃO`: validação formal de CPF, CNPJ, telefone e CNH.
- `PENDENTE DE DEFINIÇÃO`: política de armazenamento, expiração e proteção de fotos de ocorrência.
- `PENDENTE DE DEFINIÇÃO`: SLA rígido de tempo do otimizador; o limite funcional
  aprovado é 200 volumes por cálculo síncrono.
- `RISCO IDENTIFICADO`: perfil exploratório local com volumes integralmente
  posicionáveis apontou a busca de candidatos, principalmente as verificações
  AABB de colisão, como custo dominante no limite de 200 volumes. A medição não
  define SLA; qualquer otimização que altere o resultado exige ocorrência própria,
  testes, ADR e nova `algorithm_version`.
- `PENDENTE DE DEFINIÇÃO`: mensagens finais do WhatsApp para confirmação, erro e status.
- `CONFIRMADO`: a OC21 expõe comparação transitória de 2 a 10 caminhões, aplica
  preflight integral, limita a carga compartilhada a 200 volumes e reutiliza a
  mesma engine `heuristic-v1`; não persiste, não cria `LoadPlan` e não define
  ranking, score ou vencedor. Estado da ocorrência: concluída.
- `CONFIRMADO`: a OC22 expõe explicação de plano persistido por `AIProvider`,
  possui provider fake, timeout configurável de 5 segundos por padrão e fallback
  determinístico para timeout, indisponibilidade e resposta inválida. Estado da
  ocorrência: concluída; o adapter externo concreto pertence ao Desenvolvedor 4.

## Gates detalhados do otimizador e planejamento

- `CONFIRMADO`: a `ADR-008` define os pontos candidatos da OC15, a ordem `(y, z, x, rotation_rank)`, o first-fit e os motivos `TRUCK_DIMENSIONS_EXCEEDED` e `NO_VALID_POSITION` próprios desta etapa.
- `CONFIRMADO`: conforme a `ADR-009`, a OC16 considera colisão somente a sobreposição positiva nos três eixos, permite contato por face, aresta ou vértice, usa tolerância zero e valida o candidato contra todas as caixas já posicionadas.
- `CONFIRMADO`: conforme a `ADR-010`, a OC17 considera o piso válido e exige, acima dele, 100% da base coberta pela união exata dos contatos de um ou mais suportes, sem dupla contagem ou tolerância.
- `CONFIRMADO`: toda aresta de apoio transmite carga positiva por todos os ramos; suportes diretos devem ser empilháveis e nenhum suporte ou ancestral que receba carga pode ser frágil. O candidato pode ser frágil ou não empilhável no topo e não existe limite de volume "pesado".
- `CONFIRMADO`: conforme a `ADR-011`, o controle incremental usa `Decimal`, aceita igualdade ao peso máximo e não altera o acumulado em uma tentativa excedente.
- `CONFIRMADO`: o catálogo estável segue a precedência `TRUCK_DIMENSIONS_EXCEEDED`, `TRUCK_WEIGHT_EXCEEDED`, `NON_STACKABLE_SUPPORT`, `FRAGILE_SUPPORT_WEIGHT_EXCEEDED`, `INSUFFICIENT_SUPPORT`, `COLLISION` e `NO_VALID_POSITION`; entrada inválida não é rejeição de volume.
- `CONFIRMADO`: conforme a `ADR-012`, ocupação é a soma dos volumes colocados dividida pelo volume interno e multiplicada por 100, em `Decimal`, com duas casas e `ROUND_HALF_UP`; a versão inicial é `heuristic-v1`.
- `CONFIRMADO`: conforme a `ADR-013`, a porta fica em `z = internal_length_cm`,
  profundidade usa a face voltada à porta e `loading_sequence` é topológica com
  suportes anteriores aos apoiados.
- `CONFIRMADO`: a OC22 prepara deterministicamente somente o contexto técnico de
  um plano persistido, sem dados pessoais de cliente ou motorista. A IA e o
  fallback não recalculam, validam ou modificam o plano; erros `401`, `403`, `404`
  e plano tecnicamente inválido não são mascarados pelo fallback.
- `CONFIRMADO`: conforme a `ADR-014`, FKs preservam proveniência, snapshots
  preservam valores calculados e itens referenciados não podem ser substituídos.

`CONFIRMADO`: a OC20 integra OC11 a OC19 em uma engine `heuristic-v1`, persiste
o resultado com snapshots e expõe criação, detalhe, visualização, aprovação e
recálculo protegidos por RBAC.

`CONFIRMADO`: a expansão usa identidade `(order_item_id, volume_index)` com índice 1-based e não expõe política alternativa de base.

`CONFIRMADO`: a OC21 compara de 2 a 10 caminhões com a engine existente e retorna
um array de resultados independentes, na ordem solicitada e sem significado de
preferência. Falta de espaço em candidato válido é resultado normal; somente falha
de preflight encerra a requisição inteira.

`RISCO IDENTIFICADO`: mudança futura em gate determinístico exige testes, ADR e
nova `algorithm_version`; a representação JSON de `Decimal` segue D06 e
`ADR-016`, sem alterar a aritmética determinística da OC20.

## Suposições técnicas

- `SUPOSIÇÃO TÉCNICA`: o backend seguirá sessão SQLAlchemy síncrona, conforme `backend/AGENTS.md`, até decisão explícita em contrário.
- `SUPOSIÇÃO TÉCNICA`: exclusões de cadastros principais serão lógicas por `active = false` quando houver histórico ou vínculo.
- `SUPOSIÇÃO TÉCNICA`: IDs UUID podem ser gerados pela aplicação ou banco, desde que o padrão seja único e documentado na primeira migration.
- `CONFIRMADO`: fotos de ocorrência aceitam apenas referência mock controlada;
  não há storage local binário no MVP.
- `CONFIRMADO`: sessões opacas expiram após 30 minutos de inatividade ou 8 horas
  absolutas, conforme D18 e `ADR-020`.
- `CONFIRMADO`: novos hashes usam Argon2id m=19 MiB, t=2 e p=1; PBKDF2 fica
  restrito à migração gradual após login válido.

## Riscos identificados

- `CONFIRMADO`: o risco de dependências vulneráveis registrado em 2026-08-06 foi
  corrigido em 2026-08-07. A validação histórica da OC60, em 2026-08-09,
  registrou zero achados, lint, 159 testes e build; esses resultados não
  representam a auditoria atual da release, registrada abaixo.
- `RISCO IDENTIFICADO`: a blocklist embutida é intencionalmente limitada. A
  operação pode montar um arquivo UTF-8 de até 100 mil entradas, mas ainda deve
  escolher uma fonte confiável e definir sua rotina de atualização.
- `CONFIRMADO`: Caddy encerra TLS, redireciona HTTP, preserva CSP/HSTS e remove a
  assinatura do backend na referência de produção. Certificado, DNS e headers
  ainda precisam ser verificados no domínio real antes da publicação.
- `CONFIRMADO`: a suíte migrou do adaptador `httpx` descontinuado para `httpx2`;
  o registro histórico da OC61 contém 941 testes, não a contagem atual.
- `RISCO IDENTIFICADO`: a cena 3D continua sendo o maior chunk do frontend.
  O build bloqueia regressões acima de 250 KiB gzip; a medição atual consta na
  auditoria da release abaixo. Tempo de parse e GPU devem ser medidos em
  equipamento operacional representativo.
- `CONFIRMADO`: o projeto fixa Node 22.23.1 nos Dockerfiles e em `.nvmrc`;
  validações devem usar essa versão. O relato antigo sobre Node global 22.16
  descrevia uma estação específica, não um requisito ou bloqueio do projeto.
- `CONFIRMADO`: o risco de bloqueio permanente do início da viagem foi resolvido
  pela persistência do carregamento. A OC09 continua exigindo `FINISHED` para o
  mesmo plano e falha fechado em qualquer ausência ou divergência.
- `RISCO IDENTIFICADO`: cancelamento, falha, ausência, atraso e reentrega não
  fazem parte da máquina de estados da OC09 e exigem decisão, migration e testes
  antes de serem aceitos.
- `RISCO IDENTIFICADO`: o Quality Gate remoto do PR #17 apontou uma
  vulnerabilidade média no `frontend/Dockerfile.production`: a instalação npm
  não usa `--ignore-scripts`. O achado não é de CORS e pertence ao bloco de
  frontend/infra, não ao backend da OC09.
- `RISCO IDENTIFICADO`: o documento-base usa nomes de tabelas em português, enquanto o projeto já decidiu nomes técnicos em inglês. A documentação atual mantém inglês para evitar divergência no código.
- `RISCO IDENTIFICADO`: o roadmap antigo usava outra numeração de ocorrências. A partir desta revisão, usar `OC01` a `OC48`.
- `RISCO IDENTIFICADO`: criar lógica geométrica no frontend pode gerar divergência entre visualização e validação do backend.
- `RISCO IDENTIFICADO`: aceitar resposta de IA sem schema pode atualizar status indevido.
- `RISCO IDENTIFICADO`: criar migrations grandes com vários módulos aumenta conflito entre os 4 desenvolvedores.
- `RISCO IDENTIFICADO`: seeds com dados pessoais reais violam as regras do projeto.
- `CONFIRMADO`: `SECRET_KEY=local-only` ou valor fraco só funciona em ambiente
  local; a validação impede inicialização em produção.

## Auditoria da preparação v1.0.0 — 2026-09-09

`CONFIRMADO`: preparação autorizada a partir de `desenvolvimento`, base
`a685c51`, na branch `release/v1.0.0`. A versão da aplicação passa de `0.1.0`
para `1.0.0` em FastAPI, `package.json` e nos dois metadados raiz do lock npm.
Na primeira etapa, as dependências foram preservadas; a etapa seguinte autorizou
as correções pontuais de segurança descritas abaixo. `/api/v1`, `heuristic-v1`,
migrations e regras de domínio permanecem iguais.
Não há commit, push, merge, tag ou GitHub Release nesta preparação.

### Verificações iniciais, antes das correções dos bloqueadores

`CONFIRMADO`: Python 3.12.1 com instalação isolada de
`requirements-dev.lock.txt` por hashes, Node 22.23.1 e PostgreSQL 16 exclusivo de
teste. Resultados desta execução, sem substituir registros históricos:

- Ruff check e format check: aprovados, 261 arquivos formatados.
- `pytest -q tests --cov=app --cov-report=term`: 1.143 testes aprovados,
  cobertura total de 94%. A fixture aplica migrations do banco vazio, downgrade
  mínimo e upgrade; `alembic upgrade head`, `current` e `check` também passaram,
  com head `20260830_0011` e sem operações novas detectadas.
- `npm ci --ignore-scripts`, lint, 300 testes em 42 arquivos e build: aprovados.
  O orçamento da cena 3D passou com 215,6 KiB gzip para limite de 250 KiB.
- Compose local, teste e produção: `config --quiet` aprovado. Produção foi
  validada com placeholders e domínio reservado `example.test`, sem subir
  serviços ou validar DNS/TLS real.
- Build da imagem backend com `--pull` e Trivy com os parâmetros da CI:
  aprovados, sem achados `HIGH,CRITICAL` com correção disponível
  (`--ignore-unfixed`). O PostgreSQL de teste foi removido após a validação.
- `npm audit --audit-level=high`: reprovado, com 1 vulnerabilidade alta e
  2 moderadas; detalhes abaixo.
- `git diff --check`, links locais da documentação e versão OpenAPI:
  aprovados. Comparação estrutural dos manifestos confirmou que somente a
  versão da aplicação mudou, sem mudanças na árvore de dependências.
- Revisão das adições para chaves privadas, tokens, credenciais em URLs,
  atribuições de segredos e URLs pessoais de Codespaces: nenhum achado.

### Achados da auditoria e acompanhamento

- `CONFIRMADO`: a auditoria npm inicial apontou `js-yaml` como alta
  (`GHSA-2883-xcg3-v3hh`) e `@vitest/mocker`/`vitest` como moderadas
  (`GHSA-82fw-gwwq-j7x9`). São dependências de desenvolvimento da árvore
  instalada. A primeira etapa não autorizava mudar dependências; a solicitação
  posterior autorizou a menor atualização segura, registrada abaixo.
- `CONFIRMADO`: `changeDeliveryStatus` em
  `frontend/src/features/deliveries/api/tripsApi.ts` interpretava `TripDto`, mas
  `PATCH /deliveries/{id}/status` retorna `DeliveryRead`. Uma reprodução isolada
  com o adapter real e resposta fake no contrato backend confirmou `TypeError`
  ao ler `deliveries.map`. A atualização podia ser persistida pelo backend e a
  interface exibir erro sem atualizar a viagem. O adapter e a cobertura desse
  contrato foram corrigidos na etapa seguinte autorizada para a release.
- `RISCO IDENTIFICADO`: `tripsErrorMessages.ts` ainda informa que carregamento
  não existe. O backend já o implementa; corrigir esse texto de interface em
  tarefa própria. Os READMEs foram corrigidos nesta preparação.
- `CONFIRMADO`: a equipe autorizou alinhar documentalmente o RBAC de
  carregamento, ocorrências e relatórios ao comportamento atual da v1.0.0.
  A matriz e as regras em `docs/04` refletem essa decisão, sem mudar permissões
  implementadas ou o restante do RBAC. A ausência de consulta pública de
  histórico geral permanece registrada em `docs/04`.
- `RISCO IDENTIFICADO`: caminhão/motorista ativo não significa disponível para
  uma nova viagem. Não há prevenção de conflitos entre viagens distintas,
  conforme auditoria de models, services e repositories registrada no roadmap.
- `CONFIRMADO`: OC21 e OC22 existem no backend, mas a tela de planejamento ainda
  não consome comparação nem explicação; não foi adicionada integração de UI.
- `RISCO IDENTIFICADO`: Pytest emite aviso de depreciação de `crypt` pelo
  `passlib`; Vitest emite erros de conexão recusada em requisições do jsdom,
  apesar de todos os testes passarem. Investigar isolamento dos mocks em tarefa
  própria; esses avisos não foram mascarados.

`CONFIRMADO`: os dois bloqueadores técnicos foram corrigidos e a divergência
documental dos três recursos de RBAC foi conciliada por decisão da equipe.
Os checks aprovados não equivalem a uma
homologação completa em navegador nem à validação do ambiente real de produção.

`PENDENTE DE DEFINIÇÃO`: WhatsApp real, Grok/xAI, conversas e automações por IA
externa, distribuição entre caminhões e ViaCEP constam somente como evoluções
no [roadmap pós-v1.0.0](10-roadmap-inicial.md#roadmap-pós-v100). Recuperação de
senha, MFA, validações formais de CPF/CNPJ/CNH/telefone, storage de fotos e
observabilidade continuam pendentes; a release não os declara concluídos.

### Correções autorizadas dos bloqueadores

`CONFIRMADO`: a solicitação posterior da preparação autoriza corrigir somente
o consumo de `DeliveryRead` no frontend e as dependências vulneráveis. A
preparação anterior foi preservada, sem commit, stash, reset ou publicação.

`CONFIRMADO`: `changeDeliveryStatus` usa `api.patch<DeliveryDto>`, mapeia a
entrega e recarrega a viagem pelo `trip_id` da resposta. A assinatura permanece
compatível com `TripPage` e `useTripPage`; nenhuma resposta de backend ou regra
de domínio mudou. Testes novos usam o adapter e o hook reais com HTTP simulado,
incluindo o ciclo de entrega, espera pelo GET, falha de PATCH e falha de recarga.

`CONFIRMADO`: antes da atualização foram executados `npm audit`,
`npm audit --json` e `npm audit --omit=dev --audit-level=moderate`.
Os dois primeiros retornaram 3 achados; o último retornou zero.

| Pacote e cadeia instalada antes | Tipo/uso | Severidade | Correção mínima |
|---|---|---|---|
| `eslint 9.39.5 -> @eslint/eslintrc 3.3.6 -> js-yaml 4.3.1` | Transitiva, lint | Alta | `js-yaml 4.3.2` |
| `vitest 4.1.10` | Direta, testes | Moderada | `vitest 4.1.11` |
| `vitest 4.1.10 -> @vitest/mocker 4.1.10` | Transitiva, testes | Moderada | `@vitest/mocker 4.1.11` |

`CONFIRMADO`: `js-yaml` é afetado por consumo excessivo de CPU ao processar
merges YAML vazios, corrigido na versão `4.3.2`
([GHSA-2883-xcg3-v3hh / CVE-2026-84375](https://github.com/advisories/GHSA-2883-xcg3-v3hh)).
Vitest/mocker compartilham o advisory de leitura de arquivos por redirect mock,
corrigido em `4.1.11`
([GHSA-82fw-gwwq-j7x9 / CVE-2026-84373](https://github.com/advisories/GHSA-82fw-gwwq-j7x9)).
Todos estão na árvore de desenvolvimento; não compõem o runtime estático servido
pelo Caddy. Isso não dispensa corrigir ferramentas de desenvolvimento e CI.

`CONFIRMADO`: são patches dentro das mesmas versões major/minor; Vitest continua
compatível com Node `>=22.22 <23`. O pin direto passa a `4.1.11`; o lock atualiza
os sete pacotes `@vitest/*` instalados para a versão exigida pelo Vitest e
`js-yaml` para `4.3.2`, compatível com a dependência do ESLint. Nenhum pacote de
runtime, override, ignore, dependência nova ou `npm audit fix --force` foi usado.

`CONFIRMADO`: npm 10.9.8 falhou internamente ao resolver a atualização
(`edgesOut`). O lock foi resolvido com npm 11.9.0 já disponível, executado sob
Node 22.23.1. A atualização incidental de `@jridgewell/sourcemap-codec` foi
excluída desta mudança, preservando `1.5.5` compatível com `magic-string`.
`npm ci --ignore-scripts` com npm 10.9.8 instalou o lock resultante com sucesso.

### Verificação após as correções

`CONFIRMADO`: com Node 22.23.1, npm 10.9.8 e o lock atualizado, passaram
`npm ci --ignore-scripts`, `npm run lint`, os 306 testes em 44 arquivos de
`npm test -- --run` e `npm run build`. O orçamento 3D permaneceu em 215,6 KiB
gzip, abaixo de 250 KiB. `npm audit`, `npm audit --audit-level=high` e
`npm audit --omit=dev --audit-level=moderate` retornaram zero vulnerabilidades.

`CONFIRMADO`: Ruff check e format check passaram novamente; Pytest completo
com a configuração de cobertura da CI aprovou 1.143 testes e 94% de cobertura
em PostgreSQL 16. Inclui integração das rotas de entrega e o E2E
`test_complete_v1_flow`, que percorre viagem/entrega por comandos controlados.
O novo teste de tela percorre `PENDING -> IN_DELIVERY -> DELIVERED` usando PATCH
e GET simulados com o adapter real. Compose local e `git diff --check` passaram.

`CONFIRMADO`: os dois bloqueadores solicitados estão corrigidos. A revisão de
escopo manteve as alterações de versão, release, documentação obsoleta, roadmap,
contrato frontend e segurança; não identificou implementação fora do escopo.
WhatsApp real, Grok/xAI, ViaCEP, distribuição entre caminhões e GPS/rastreamento
continuam futuros, sem integração implementada ou declaração de entrega.

`CONFIRMADO`: o ajuste documental final registra `ADMIN` consultando
carregamento e ocorrências; `LOGISTICS_MANAGER` e `CHECKER` criando e operando
carregamento/checklist, sem atribuição a conferente; `LOGISTICS_MANAGER` criando
e consultando ocorrências e `DRIVER` fazendo isso somente nas próprias
viagens/entregas. `DRIVER` não acessa carregamento e `CHECKER` não acessa
ocorrências na v1.0.0. Somente `ADMIN` e `LOGISTICS_MANAGER` geram e consultam
relatórios; `CHECKER` e `DRIVER` não têm acesso.

`PENDENTE DE DEFINIÇÃO`: atribuição de carregamento a conferente, autorização
por objeto para `CHECKER`, possível consulta de carregamento pelo `DRIVER`,
ocorrência vinculada ao carregamento/durante conferência com acesso do `CHECKER`,
relatório de carregamento para `CHECKER` e relatório da própria viagem para
`DRIVER` permanecem no roadmap pós-v1.0.0.

`RECOMENDAÇÃO`: **READY para v1.0.0**, considerando as verificações anteriores,
as correções dos dois bloqueadores técnicos e a decisão documental de RBAC.
O texto obsoleto de carregamento e os avisos de `passlib`/jsdom continuam
registrados como pendências de manutenção, sem impedir os checks já aprovados.
Este ajuste final é somente documental e não representa publicação da release.

## Recomendações de manutenção

- `RECOMENDAÇÃO`: registrar novas decisões estruturais como ADR antes de implementar.
- `RECOMENDAÇÃO`: manter cada PR limitado a uma ocorrência ou a uma fatia pequena e testável.
- `RECOMENDAÇÃO`: atualizar este documento quando uma pendência for resolvida ou virar ADR.
- `RECOMENDAÇÃO`: revisar `docs/03`, `docs/04`, `docs/05`, `docs/08` e `docs/09` antes de iniciar ocorrências que alterem banco, regra, API ou padrão.
