# Riscos, pendências e decisões necessárias

Este documento concentra pontos que ainda precisam de validação da equipe. Não use itens daqui como decisão aprovada enquanto estiverem marcados como pendência, suposição ou risco.

## Decisões já confirmadas

- `CONFIRMADO`: arquitetura de monólito modular, conforme `ADR-001`.
- `CONFIRMADO`: unidades em centímetros, quilogramas e coordenadas `x/y/z`, conforme `ADR-002`.
- `CONFIRMADO`: IA como apoio, não como validadora física, conforme `ADR-003`.
- `CONFIRMADO`: endpoints públicos, matriz RBAC e bootstrap do primeiro administrador, conforme `ADR-004`.
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
- `CONFIRMADO`: o contrato aprovado mantém login, token JWT e `/auth/me`, remove `/auth/register` e restringe criação de usuários a `ADMIN` após bootstrap local.
- `CONFIRMADO`: a `OC51-I` auditou a matriz completa de autorização e a fronteira pública de todos os endpoints atualmente implementados.
- `CONFIRMADO`: conforme `D17`, a comparação básica e determinística da OC21
  integra o MVP depois da OC20 e aceita no máximo 10 caminhões por execução; a
  comparação automática avançada permanece futura.

## Decisões necessárias

- `DECISÃO NECESSÁRIA`: definir comportamento quando checklist de carregamento tiver divergência.
- `DECISÃO NECESSÁRIA`: definir regra para finalizar viagem com entregas canceladas, recusadas ou falhas.
- `DECISÃO NECESSÁRIA`: definir formato final de relatório PDF e se haverá envio por e-mail/WhatsApp no MVP.
- `DECISÃO NECESSÁRIA`: OC21 — definir body, resposta, status de sucesso, catálogo
  de erros e ordenação do contrato público de `POST /load-plans/compare-trucks`.
- `DECISÃO NECESSÁRIA`: OC21 — definir critérios de ranking, pesos, desempates e
  se haverá indicação ou escolha automática de um caminhão vencedor.
- `DECISÃO NECESSÁRIA`: OC21 — definir se a comparação será persistida, se criará
  algum `load_plan` e qual candidato poderia originá-lo.
- `DECISÃO NECESSÁRIA`: OC21 — definir tratamento de IDs duplicados, caminhões
  inativos ou inexistentes e falha parcial em apenas um dos candidatos.
- `DECISÃO NECESSÁRIA`: OC21 — formalizar o RBAC específico do endpoint. A matriz
  geral exige autenticação, menor privilégio e negação por padrão, mas ainda não
  descreve expressamente a operação de comparação.
- `DECISÃO NECESSÁRIA`: OC22 — definir endpoint, request, response, schema público,
  subconjunto de dados enviado ao modelo, política de fallback e prompt final.

## Pendências técnicas

- `PENDENTE DE DEFINIÇÃO`: CI real ainda não está implementada, apenas documentada em `infra/ci/README.md`.
- `PENDENTE DE DEFINIÇÃO`: models e migrations de carregamento, entregas e
  ocorrências.
- `PENDENTE DE DEFINIÇÃO`: contrato, filtros e entidades aceitas na consulta protegida de histórico; `D01` impede consulta pública e `D02` limita a leitura geral a `ADMIN` e `LOGISTICS_MANAGER`.
- `PENDENTE DE DEFINIÇÃO`: estratégia final de logging estruturado.
- `PENDENTE DE DEFINIÇÃO`: política final de expiração de token, fluxo de refresh e bloqueio por tentativas inválidas.
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
nova `algorithm_version`; a representação JSON de `Decimal` permanece fora da
OC20.

## Suposições técnicas

- `SUPOSIÇÃO TÉCNICA`: o backend seguirá sessão SQLAlchemy síncrona, conforme `backend/AGENTS.md`, até decisão explícita em contrário.
- `SUPOSIÇÃO TÉCNICA`: exclusões de cadastros principais serão lógicas por `active = false` quando houver histórico ou vínculo.
- `SUPOSIÇÃO TÉCNICA`: IDs UUID podem ser gerados pela aplicação ou banco, desde que o padrão seja único e documentado na primeira migration.
- `SUPOSIÇÃO TÉCNICA`: fotos de ocorrência no MVP podem usar URL mock ou storage local controlado até definição de provider.
- `SUPOSIÇÃO TÉCNICA`: token JWT usa expiração configurável com default local de 60 minutos até decisão final de segurança.
- `SUPOSIÇÃO TÉCNICA`: hash de senha usa `pbkdf2_sha256` via Passlib nesta etapa, sem adicionar dependência externa nova.

## Riscos identificados

- `RISCO IDENTIFICADO`: ainda não existe vínculo entre `users` e `drivers`; por segurança, `DRIVER` não recebe acesso operacional até que esse relacionamento seja aprovado e implementado.
- `RISCO IDENTIFICADO`: o documento-base usa nomes de tabelas em português, enquanto o projeto já decidiu nomes técnicos em inglês. A documentação atual mantém inglês para evitar divergência no código.
- `RISCO IDENTIFICADO`: o roadmap antigo usava outra numeração de ocorrências. A partir desta revisão, usar `OC01` a `OC48`.
- `RISCO IDENTIFICADO`: criar lógica geométrica no frontend pode gerar divergência entre visualização e validação do backend.
- `RISCO IDENTIFICADO`: aceitar resposta de IA sem schema pode atualizar status indevido.
- `RISCO IDENTIFICADO`: criar migrations grandes com vários módulos aumenta conflito entre os 4 desenvolvedores.
- `RISCO IDENTIFICADO`: seeds com dados pessoais reais violam as regras do projeto.
- `RISCO IDENTIFICADO`: `SECRET_KEY=local-only` ou valor fraco só pode ser usado em ambiente local.

## Recomendações

- `RECOMENDAÇÃO`: registrar novas decisões estruturais como ADR antes de implementar.
- `RECOMENDAÇÃO`: manter cada PR limitado a uma ocorrência ou a uma fatia pequena e testável.
- `RECOMENDAÇÃO`: atualizar este documento quando uma pendência for resolvida ou virar ADR.
- `RECOMENDAÇÃO`: revisar `docs/03`, `docs/04`, `docs/05`, `docs/08` e `docs/09` antes de iniciar ocorrências que alterem banco, regra, API ou padrão.
