# Riscos, pendências e decisões necessárias

Este documento concentra pontos que ainda precisam de validação da equipe. Não use itens daqui como decisão aprovada enquanto estiverem marcados como pendência, suposição ou risco.

## Decisões já confirmadas

- `CONFIRMADO`: arquitetura de monólito modular, conforme `ADR-001`.
- `CONFIRMADO`: unidades em centímetros, quilogramas e coordenadas `x/y/z`, conforme `ADR-002`.
- `CONFIRMADO`: IA como apoio, não como validadora física, conforme `ADR-003`.
- `CONFIRMADO`: tecnologias oficiais descritas em `README.md` e `docs/02-arquitetura.md`.
- `CONFIRMADO`: nomes técnicos em inglês.
- `CONFIRMADO`: documentação oficial dentro da estrutura existente de `docs`.
- `CONFIRMADO`: Alembic configurado em `backend/alembic.ini` e `backend/migrations/env.py`.
- `CONFIRMADO`: migration inicial `20260729_0001` cria `users`, `customers`, `drivers`, `trucks` e `products`.
- `CONFIRMADO`: migration `20260730_0002` cria `orders` e `order_items`.
- `CONFIRMADO`: migration `20260730_0003` cria `status_history`.
- `CONFIRMADO`: autenticação inicial possui cadastro, login, token JWT e `/auth/me`.

## Decisões necessárias

- `DECISÃO NECESSÁRIA`: confirmar se comparação entre caminhões (`OC21`) faz parte do MVP obrigatório ou se fica para funcionalidade futura.
- `DECISÃO NECESSÁRIA`: decidir se haverá tabela separada `volumes` ou se volumes individuais continuarão gerados a partir de `order_items.quantity` e persistidos em `load_plan_items`.
- `DECISÃO NECESSÁRIA`: definir matriz de permissões por perfil para todos os endpoints.
- `DECISÃO NECESSÁRIA`: definir política de recálculo/versionamento para plano já aprovado.
- `DECISÃO NECESSÁRIA`: definir comportamento quando checklist de carregamento tiver divergência.
- `DECISÃO NECESSÁRIA`: definir regra para finalizar viagem com entregas canceladas, recusadas ou falhas.
- `DECISÃO NECESSÁRIA`: definir formato final de relatório PDF e se haverá envio por e-mail/WhatsApp no MVP.

## Pendências técnicas

- `PENDENTE DE DEFINIÇÃO`: CI real ainda não está implementada, apenas documentada em `infra/ci/README.md`.
- `PENDENTE DE DEFINIÇÃO`: models e migrations de planejamento, carregamento, entregas e ocorrências.
- `PENDENTE DE DEFINIÇÃO`: endpoint público e permissões para consulta de histórico de status.
- `PENDENTE DE DEFINIÇÃO`: estratégia final de logging estruturado.
- `PENDENTE DE DEFINIÇÃO`: política final de expiração de token, fluxo de refresh e bloqueio por tentativas inválidas.
- `PENDENTE DE DEFINIÇÃO`: validação formal de CPF, CNPJ, telefone e CNH.
- `PENDENTE DE DEFINIÇÃO`: política de armazenamento, expiração e proteção de fotos de ocorrência.
- `PENDENTE DE DEFINIÇÃO`: metas de performance do otimizador.
- `PENDENTE DE DEFINIÇÃO`: mensagens finais do WhatsApp para confirmação, erro e status.

## Suposições técnicas

- `SUPOSIÇÃO TÉCNICA`: o backend seguirá sessão SQLAlchemy síncrona, conforme `backend/AGENTS.md`, até decisão explícita em contrário.
- `SUPOSIÇÃO TÉCNICA`: exclusões de cadastros principais serão lógicas por `active = false` quando houver histórico ou vínculo.
- `SUPOSIÇÃO TÉCNICA`: IDs UUID podem ser gerados pela aplicação ou banco, desde que o padrão seja único e documentado na primeira migration.
- `SUPOSIÇÃO TÉCNICA`: fotos de ocorrência no MVP podem usar URL mock ou storage local controlado até definição de provider.
- `SUPOSIÇÃO TÉCNICA`: token JWT usa expiração configurável com default local de 60 minutos até decisão final de segurança.
- `SUPOSIÇÃO TÉCNICA`: hash de senha usa `pbkdf2_sha256` via Passlib nesta etapa, sem adicionar dependência externa nova.

## Riscos identificados

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
