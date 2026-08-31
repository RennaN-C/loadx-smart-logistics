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
  declaradas em `requirements.txt` e são instaladas do
  `requirements.lock.txt`, com versões resolvidas, hashes e
  `--require-hashes`.
- `CONFIRMADO`: a CI do frontend usa o Node definido em `.nvmrc`, instala com
  `npm ci --ignore-scripts` e executa ESLint, Vitest e build.
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
- `CONFIRMADO`: a camada interna da OC21 é transitória, não ranqueada, limitada a
  10 candidatos e reutiliza integralmente a mesma engine `heuristic-v1`; não
  persiste comparação nem registro SQLAlchemy `load_plan`, não define vencedor e
  não expõe API pública. Estado da ocorrência: parcial.
- `CONFIRMADO`: a fatia interna da OC22 é somente um builder determinístico de
  contexto baseado em dados já calculados, sem provider e sem mutação do plano.
  Estado da ocorrência: parcial e bloqueado por decisão; a integração real com IA
  depende da interface e do provider sob responsabilidade do Desenvolvedor 4 e
  das decisões públicas da OC22.

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
- `CONFIRMADO`: a OC22 pode preparar deterministicamente o contexto de um
  plano já calculado, mas contrato público, provider, fallback e prompt permanecem
  pendentes; a IA não recalcula, valida ou modifica o plano. Estado da ocorrência:
  parcial e bloqueado por decisão.
- `CONFIRMADO`: conforme a `ADR-014`, FKs preservam proveniência, snapshots
  preservam valores calculados e itens referenciados não podem ser substituídos.

`CONFIRMADO`: a OC20 integra OC11 a OC19 em uma engine `heuristic-v1`, persiste
o resultado com snapshots e expõe criação, detalhe, visualização, aprovação e
recálculo protegidos por RBAC.

`CONFIRMADO`: a expansão usa identidade `(order_item_id, volume_index)` com índice 1-based e não expõe política alternativa de base.

`CONFIRMADO`: a OC21 interna compara até 10 caminhões com a engine existente e
retorna resultados independentes sem ranking. Estado da ocorrência: parcial. Até
aprovação das decisões acima, ela não persiste dados nem registros SQLAlchemy de
plano e não expõe o endpoint reservado.

`RISCO IDENTIFICADO`: mudança futura em gate determinístico exige testes, ADR e
nova `algorithm_version`; a representação JSON de `Decimal` segue D06 e
`ADR-016`, sem alterar a aritmética determinística da OC20.

## Suposições técnicas

- `SUPOSIÇÃO TÉCNICA`: o backend seguirá sessão SQLAlchemy síncrona, conforme `backend/AGENTS.md`, até decisão explícita em contrário.
- `SUPOSIÇÃO TÉCNICA`: exclusões de cadastros principais serão lógicas por `active = false` quando houver histórico ou vínculo.
- `SUPOSIÇÃO TÉCNICA`: IDs UUID podem ser gerados pela aplicação ou banco, desde que o padrão seja único e documentado na primeira migration.
- `SUPOSIÇÃO TÉCNICA`: fotos de ocorrência no MVP podem usar URL mock ou storage local controlado até definição de provider.
- `CONFIRMADO`: sessões opacas expiram após 30 minutos de inatividade ou 8 horas
  absolutas, conforme D18 e `ADR-020`.
- `CONFIRMADO`: novos hashes usam Argon2id m=19 MiB, t=2 e p=1; PBKDF2 fica
  restrito à migração gradual após login válido.

## Riscos identificados

- `CONFIRMADO`: o risco de dependências vulneráveis registrado em 2026-08-06 foi
  corrigido em 2026-08-07; o `package-lock.json` atualizado retorna zero achados
  no `npm audit` e passou por lint, 159 testes e build de produção na validação
  da OC60 em 2026-08-09.
- `RISCO IDENTIFICADO`: a blocklist embutida é intencionalmente limitada. A
  operação pode montar um arquivo UTF-8 de até 100 mil entradas, mas ainda deve
  escolher uma fonte confiável e definir sua rotina de atualização.
- `CONFIRMADO`: Caddy encerra TLS, redireciona HTTP, preserva CSP/HSTS e remove a
  assinatura do backend na referência de produção. Certificado, DNS e headers
  ainda precisam ser verificados no domínio real antes da publicação.
- `CONFIRMADO`: a suíte migrou do adaptador `httpx` descontinuado para `httpx2`;
  os 941 testes de backend passaram sem o aviso anterior.
- `RISCO IDENTIFICADO`: o chunk lazy da visualização 3D ainda possui cerca de
  827 KB bruto, embora tenha 218 KB gzip no relatório do Vite. O build bloqueia
  regressões acima de 250 KiB gzip, mas tempo de parse e GPU devem ser medidos em
  equipamento operacional representativo.
- `CONFIRMADO`: o projeto fixa Node 22.23.1 nos Dockerfiles e em `.nvmrc`. O Node
  global 22.16 desta estação ainda impede o controlador visual externo, sem
  afetar build, testes ou runtime do projeto.
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

## Recomendações

- `RECOMENDAÇÃO`: registrar novas decisões estruturais como ADR antes de implementar.
- `RECOMENDAÇÃO`: manter cada PR limitado a uma ocorrência ou a uma fatia pequena e testável.
- `RECOMENDAÇÃO`: atualizar este documento quando uma pendência for resolvida ou virar ADR.
- `RECOMENDAÇÃO`: revisar `docs/03`, `docs/04`, `docs/05`, `docs/08` e `docs/09` antes de iniciar ocorrências que alterem banco, regra, API ou padrão.
