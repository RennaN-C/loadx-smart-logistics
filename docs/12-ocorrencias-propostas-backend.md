# Ocorrências propostas para o backend

## Estado deste documento

`RECOMENDAÇÃO`: este documento reúne ocorrências prontas para serem copiadas para o GitHub Projects após revisão da equipe.

`CONFIRMADO`: os identificadores `OC49` a `OC60` nasceram como sugestões. O
estado individual abaixo registra quais ocorrências foram aprovadas, integradas
ou continuam pendentes de decisão da equipe.

`CONFIRMADO`: nenhuma ocorrência abaixo está aprovada apenas por constar neste documento. Cada uma deve receber responsável, revisão de escopo e aceite da equipe antes da implementação.

`CONFIRMADO`: `OC49`, `OC50` e `OC51` já foram integradas em
`desenvolvimento`. `OC55` e `OC53` foram aprovadas por solicitação explícita do
responsável em 2026-08-04. `OC52` foi desbloqueada pela aprovação formal de D04
e D05 em 2026-08-06. `OC56` foi desbloqueada por D06 na mesma data. D12 foi
aprovada em 2026-08-07 e desbloqueou a `OC59`. `OC52`, `OC53`, `OC55`, `OC56`
e `OC59` foram integradas em `desenvolvimento` pelo PR #14.

`CONFIRMADO`: a `OC58` está implementada e validada localmente, pendente de PR e
revisão.

`CONFIRMADO`: D07 a D10 e D21 foram aprovadas em 2026-08-09. A `OC09` está
implementada e validada localmente na branch `rennan`, pendente de PR e revisão;
o início real da viagem permanece bloqueado de forma segura até o módulo de
carregamento confirmar `FINISHED`.

## Resumo de prioridade

| Identificador sugerido | Prioridade | Responsável primário sugerido | Situação |
|---|---|---|---|
| `OC49` | Alta | Desenvolvedor 1 | Integrada em `desenvolvimento` |
| `OC50` | Alta | Desenvolvedor 1 | Integrada em `desenvolvimento` |
| `OC51` | Alta | Desenvolvedor 1 | Integrada em `desenvolvimento` |
| `OC52` | Alta | Desenvolvedor 1 | Integrada em `desenvolvimento` |
| `OC53` | Alta | Desenvolvedor 1, com revisão do Desenvolvedor 4 | Integrada em `desenvolvimento` |
| `OC54` | Média | Desenvolvedor 4, com apoio do Desenvolvedor 1 | Pronta para aprovação |
| `OC55` | Média | Desenvolvedor 1, com revisão do Desenvolvedor 4 | Integrada em `desenvolvimento` |
| `OC56` | Média | Desenvolvedor 1 e Desenvolvedor 3 | Integrada em `desenvolvimento` |
| `OC57` | Média | Desenvolvedor 2 | Absorvida e resolvida pela revisão da `OC11` |
| `OC58` | Baixa | Desenvolvedor 1, com apoio do Desenvolvedor 4 | Implementada e validada localmente; pendente de PR e revisão |
| `OC59` | Média | Desenvolvedor 1 e Desenvolvedor 3 | Integrada em `desenvolvimento` |
| `OC60` | Alta | Desenvolvedor 1 | Aprovada por D18; em implementação |

As referências `DXX` apontam para `docs/decisoes-equipe-backend.txt`.

---

## [OC49] Corrigir atualizações parciais com valores nulos e mapear erros de integridade

- **Tipo:** correção de bug.
- **Responsável primário sugerido:** Desenvolvedor 1.
- **Prioridade:** alta.

### Objetivo

Impedir que `PATCH` aceite `null` em campos obrigatórios e garantir que violações de banco sejam convertidas no código de erro correspondente à causa real.

### Comportamento atual

`CONFIRMADO`: os schemas de atualização aceitam `null` em campos não anuláveis. Quando o banco rejeita o valor, os services convertem qualquer `IntegrityError` em duplicidade de e-mail, documento, código ou placa, ou em cliente de pedido inexistente.

### Critérios de aceite

- Campos omitidos no `PATCH` permanecem inalterados.
- Campos anuláveis documentados continuam aceitando `null`.
- Campos obrigatórios retornam `422` no formato padrão quando recebem `null`.
- Duplicidades continuam retornando `409` com o código específico documentado.
- Outras violações de integridade não são apresentadas como duplicidade ou entidade inexistente.
- Usuários, clientes, motoristas, caminhões, produtos e pedidos possuem testes para campo omitido, `null` permitido, `null` proibido e duplicidade.
- Nenhuma coluna, endpoint ou regra de negócio nova é criada.

### Dependências

- `docs/03-modelo-dados.md` para identificar colunas anuláveis.
- `docs/05-contratos-api.md` para preservar os códigos públicos.

### Arquivos prováveis

- `backend/app/modules/*/schemas.py`.
- `backend/app/modules/*/service.py`.
- `backend/tests/unit`.
- `backend/tests/integration`.

### Testes mínimos

- `PATCH /users/{id}` com `name = null` retorna `422`.
- `PATCH /orders/{id}` com `priority = null` retorna `422`.
- `PATCH /customers/{id}` com `notes = null` continua permitido.
- Uma duplicidade real mantém seu código `409` específico.

---

## [OC50] Padronizar todas as respostas de erro da API

- **Tipo:** correção de contrato.
- **Responsável primário sugerido:** Desenvolvedor 1.
- **Prioridade:** alta.

### Objetivo

Garantir que validações de schema, UUID inválido, erros de domínio e falhas inesperadas usem o contrato `code`, `message` e `details` definido em `docs/05-contratos-api.md`.

### Comportamento atual

`CONFIRMADO`: a `OC49` padronizou erros automáticos de validação de schema, path e query como `VALIDATION_ERROR`. Nesta ocorrência, a construção das respostas foi centralizada, erros inesperados passaram a usar `INTERNAL_SERVER_ERROR` sem expor detalhes internos e o OpenAPI passou a referenciar o schema compartilhado `ErrorResponse`.

### Critérios de aceite

- `RequestValidationError` retorna `code`, `message` e `details`.
- UUID inválido no path usa o mesmo formato.
- Erros de domínio preservam códigos estáveis em `UPPER_SNAKE_CASE`.
- Erros inesperados retornam `500` sem expor stack trace, segredo ou payload sensível.
- A criação repetida de `error_response` é substituída por solução compartilhada coerente com `app/core` ou `app/shared`.
- OpenAPI e testes refletem os erros públicos esperados.
- `docs/05-contratos-api.md` é atualizado apenas se o detalhamento do `422` precisar ser formalizado.

### Dependências

- Contrato de erros já confirmado em `docs/05-contratos-api.md`.

### Testes mínimos

- Body inválido retorna o envelope padrão.
- UUID inválido retorna o envelope padrão.
- Erro de domínio conhecido mantém código e status HTTP.
- Erro inesperado não revela detalhes internos.

---

## [OC51] Proteger endpoints e implementar autorização por perfil

- **Tipo:** segurança e funcionalidade.
- **Responsável primário sugerido:** Desenvolvedor 1.
- **Prioridade:** alta.

### Objetivo

Exigir autenticação nos endpoints de negócio e aplicar a matriz de permissões aprovada para `ADMIN`, `CHECKER`, `DRIVER` e `LOGISTICS_MANAGER`.

### Comportamento atual

`CONFIRMADO`: a `OC51-I` auditou `/auth/me` e todos os endpoints de negócio atualmente implementados contra os quatro perfis aprovados; `/auth/register` não existe mais; Swagger, ReDoc e OpenAPI são expostos somente no ambiente local.

### Critérios de aceite

- Endpoints públicos e protegidos correspondem exatamente à decisão `D01`.
- Cada rota protegida aplica a matriz aprovada em `D02`.
- A criação de usuários segue a decisão `D03`.
- Token ausente, inválido ou expirado retorna `401 AUTH_INVALID_TOKEN`.
- Usuário autenticado sem permissão retorna `403 AUTH_FORBIDDEN`.
- Usuário inativo não acessa endpoints protegidos.
- O esquema Bearer aparece no OpenAPI e pode ser usado no Swagger.
- Senha, token, documento completo e segredo não aparecem em logs.
- Há testes para acesso anônimo, papel permitido, papel negado e usuário inativo.

### Dependências

- `D01`, `D02` e `D03`: decisões aprovadas e registradas em `ADR-004`.
- Atualização simultânea de `docs/04`, `docs/05`, README de `auth` e README de `users`.

### Divisão em subocorrências pequenas

`CONFIRMADO`: a `OC51` será executada na ordem abaixo. Cada subocorrência possui um único objetivo, inclui os testes do próprio comportamento e pode virar um commit isolado. A `OC51` só será concluída depois da auditoria final.

| Subocorrência | Objetivo único | Verificação mínima | Commit sugerido |
|---|---|---|---|
| `OC51-A` | Registrar `D01`, `D02`, `D03` e `ADR-004` | `git diff --check` | `docs: registra decisões de segurança da OC51` |
| `OC51-B` | Centralizar usuário autenticado e verificação de papéis | `/auth/me`, token inválido, usuário inativo e papel negado | `refactor: centraliza autenticação e autorização` |
| `OC51-C` | Criar bootstrap local do primeiro `ADMIN` | cria no banco vazio, oculta senha e recusa nova execução | `feat: adiciona bootstrap local do primeiro administrador` |
| `OC51-D` | Remover `/auth/register` e restringir `/users` a `ADMIN` | rota removida, matriz de usuários e proteção do último administrador | `fix: restringe criação e administração de usuários` |
| `OC51-E` | Proteger clientes e motoristas | `ADMIN` lê, `LOGISTICS_MANAGER` gerencia e demais recebem `403` | `feat: aplica permissões em clientes e motoristas` |
| `OC51-F` | Proteger caminhões e produtos | `ADMIN` e `CHECKER` leem, `LOGISTICS_MANAGER` gerencia e `DRIVER` recebe `403` | `feat: aplica permissões em caminhões e produtos` |
| `OC51-G` | Proteger pedidos | `ADMIN` e `CHECKER` leem, `LOGISTICS_MANAGER` gerencia e `DRIVER` recebe `403` | `feat: aplica permissões em pedidos` |
| `OC51-H` | Restringir documentação da API por ambiente | Swagger/OpenAPI local funciona e produção não os expõe | `feat: restringe documentação da API em produção` |
| `OC51-I` | Auditar o contrato completo de segurança | matriz parametrizada, OpenAPI, suíte completa e Ruff | `test: valida contrato de autorização da OC51` |

Regras de execução:

- Não iniciar a próxima subocorrência enquanto os testes da atual falharem.
- Código e testes do mesmo comportamento ficam juntos; não separar um commit funcional de sua proteção mínima.
- Não adicionar refresh token, MFA, vínculo `users`/`drivers` ou biblioteca externa nestas subocorrências.
- Se todas as subocorrências ficarem no mesmo Pull Request, preservar um commit por linha da tabela para facilitar revisão e reversão.

### Fora do escopo

- Refresh token, MFA ou provedor externo de identidade sem nova aprovação.

---

## [OC52] Integrar mudanças de status ao histórico em transação única

- **Tipo:** correção de regra de negócio.
- **Responsável primário sugerido:** Desenvolvedor 1.
- **Prioridade:** alta.

### Objetivo

Fazer com que toda mudança permitida de status registre `old_status`, `new_status`, entidade, responsável e horário, sem permitir que entidade e histórico sejam confirmados separadamente.

### Comportamento atual

`CONFIRMADO`: a OC52 está integrada em `desenvolvimento`. O status saiu do `PATCH`
genérico, as transições manuais de D04 usam caso de uso explícito e pedido e
histórico são confirmados ou desfeitos juntos conforme D05. O método independente
de histórico mantém seu próprio `commit`, enquanto operações compostas usam
`stage_status_change` sob a transação do service dono.

### Critérios de aceite

- Status é alterado por caso de uso explícito, não por atribuição genérica sem regra.
- Somente transições aprovadas em `D04` são aceitas.
- Edições de pedido respeitam os bloqueios aprovados em `D04`.
- Histórico e entidade são persistidos na mesma transação.
- Uma falha ao registrar histórico desfaz também a alteração da entidade.
- `changed_by` segue a decisão `D05` e referencia usuário existente quando informado.
- Não é criado registro duplicado quando não existe mudança efetiva, conforme decisão registrada.
- Testes comprovam sucesso, transição inválida e rollback integral.

### Dependências

- `D04`: transições e bloqueios de edição de pedidos.
- `D05`: dono da transação e identificação do responsável.
- `OC51` para obter usuário autenticado quando a mudança for manual.

### Observação

`RECOMENDAÇÃO`: o padrão transacional aprovado nesta ocorrência deve ser reutilizado em viagens, entregas e carregamento.

---

## [OC53] Executar testes de integração em PostgreSQL com migrations Alembic

- **Tipo:** qualidade e banco de dados.
- **Responsável primário sugerido:** Desenvolvedor 1.
- **Revisor sugerido:** Desenvolvedor 4.
- **Prioridade:** alta.

### Objetivo

Fazer os testes de integração usarem PostgreSQL 16 e a cadeia real de migrations, conforme a documentação do backend.

### Comportamento atual

`CONFIRMADO`: a `OC53` substituiu SQLite por PostgreSQL 16 exclusivo na suíte de
integração. A fixture valida o alvo, recria somente o schema de teste, aplica a
cadeia Alembic, exercita `downgrade -1`, reaplica o head e isola cada teste em
transação externa com savepoints.

### Critérios de aceite

- Testes de integração usam banco PostgreSQL exclusivo de teste.
- A estrutura é criada por `alembic upgrade head`, não por `create_all`.
- A cadeia completa sobe do banco vazio até `head`.
- O downgrade mínimo aprovado é exercitado sem perda fora do banco de teste.
- FKs, checks, uniques, UUID, `Numeric` e timestamps com timezone possuem ao menos um teste real.
- Cada teste ou módulo possui isolamento determinístico de dados.
- Nenhum teste usa banco de desenvolvimento, staging ou produção.
- O README de testes descreve comandos locais e variáveis necessárias.

### Dependências

- PostgreSQL 16 já confirmado como tecnologia oficial.
- Migrations `20260729_0001` a `20260804_0004`.

### Testes mínimos

- `alembic upgrade head` em banco vazio.
- FK inválida é rejeitada.
- Constraint de dimensão/peso é aplicada pelo PostgreSQL.
- Timestamp representa instante com timezone.

---

## [OC54] Criar pipeline de CI para o backend oficial

- **Tipo:** infraestrutura e qualidade.
- **Responsável primário sugerido:** Desenvolvedor 4.
- **Apoio sugerido:** Desenvolvedor 1.
- **Prioridade:** média.

### Objetivo

Bloquear integração de alterações backend que quebrem lint, formatação, migrations ou testes no ambiente oficial.

### Critérios de aceite

- Pipeline usa Python 3.12.
- Pipeline sobe PostgreSQL 16 de teste.
- Executa `ruff check` e `ruff format --check`.
- Aplica `alembic upgrade head`.
- Executa testes unitários e de integração.
- Publica o resumo de cobertura sem inventar limite mínimo não aprovado.
- Falha em qualquer etapa bloqueia o job.
- Segredos reais não são necessários nem impressos.

### Dependências

- `OC53` para a suíte PostgreSQL.
- Comandos oficiais documentados em `docs/08-padroes-desenvolvimento.md` e README de testes.

---

## [OC55] Corrigir ciclo de vida dos testes e normalizar formatação Ruff

- **Tipo:** manutenção técnica.
- **Responsável primário sugerido:** Desenvolvedor 1.
- **Revisor sugerido:** Desenvolvedor 4.
- **Prioridade:** média.

### Objetivo

Eliminar warnings de recursos, reduzir fixtures duplicadas e deixar os arquivos Python conformes ao formatador oficial.

### Comportamento atual

`CONFIRMADO`: a `OC55` centralizou as fixtures no menor escopo coerente, passou a
encerrar `TestClient`, sessions, conexões e engines e normalizou a base Python com
Ruff. A validação final não apresentou `ResourceWarning` causado pelos testes.

### Critérios de aceite

- Fixtures compartilhadas ficam em `conftest.py` no menor escopo coerente.
- `TestClient` é fechado ao final dos testes.
- Sessions, conexões e engines são encerradas e descartadas.
- A suíte não emite `ResourceWarning` causado pelo código de teste.
- `ruff check .` e `ruff format --check .` passam.
- A mudança de formatação não altera contratos ou regras de negócio.
- Todos os cenários existentes continuam passando, além dos testes adicionados
  pelas demais ocorrências; não fixar uma contagem que ficará obsoleta.

### Dependências

- Pode ser executada antes da `OC53`, mas deve ser compatível com as fixtures PostgreSQL futuras.

---

## [OC56] Alinhar serialização de pesos e números decimais entre backend e frontend

- **Tipo:** correção de contrato.
- **Responsáveis sugeridos:** Desenvolvedor 1 e Desenvolvedor 3.
- **Prioridade:** média.

### Objetivo

Definir e aplicar uma representação JSON única para campos `Decimal`, especialmente `weight_kg` e `max_weight_kg`.

### Comportamento atual

`CONFIRMADO`: a OC56 está integrada em `desenvolvimento`. Schemas de entrada e saída,
OpenAPI, exemplos e o consumidor de caminhões usam exclusivamente número JSON.
Strings decimais são rejeitadas; `Decimal` e `Numeric` permanecem no domínio e
na persistência, sem mudança na aritmética do otimizador.

### Critérios de aceite

- A equipe registra a decisão `D06`.
- Schemas de entrada, schemas de saída e OpenAPI usam a representação aprovada.
- Documentação e exemplos usam a mesma representação.
- O frontend consome o valor sem conversão implícita ou perda silenciosa de precisão.
- Testes de contrato verificam valor e tipo JSON.
- Caminhões, produtos, pedidos futuros, planos e relatórios seguem a mesma convenção.

### Dependências

- `D06`: número JSON aprovado em 2026-08-06.
- Revisão conjunta entre backend e frontend.

### Divisão de execução aprovada

1. **OC56-A — decisão e contrato:** registrar D06, ADR-016, precisão, escala e
   exemplos oficiais.
2. **OC56-B — backend:** criar o tipo compartilhado da fronteira HTTP, aplicar
   nos schemas, rejeitar strings e validar JSON e OpenAPI.
3. **OC56-C — frontend:** remover a compatibilidade ambígua `number | string` e
   consumir o contrato como `number` sem coerção silenciosa.
4. **OC56-D — encerramento:** executar as suítes completas, atualizar READMEs e
   registrar a ocorrência como validada localmente.

---

## [OC57] Rejeitar tipos inválidos no cálculo de capacidade do caminhão

- **Tipo:** correção de domínio.
- **Responsável primário sugerido:** Desenvolvedor 2.
- **Prioridade:** média.

### Objetivo

Garantir que dimensões do cálculo de capacidade sejam inteiros positivos e que o resultado `internal_volume_cm3` permaneça inteiro.

### Comportamento atual

`CONFIRMADO`: esta proposta foi absorvida pela revisão da `OC11`. `calculate_truck_capacity` exige inteiros positivos, exclui `bool` e converte tipos inválidos em `InvalidTruckCapacityError`.

### Critérios de aceite

- `internal_width_cm`, `internal_height_cm` e `internal_length_cm` aceitam somente `int` positivo, excluindo `bool`.
- `float`, `str`, `bool` e `None` levantam `InvalidTruckCapacityError`.
- Peso continua exigindo `Decimal` positivo e finito.
- Resultado válido mantém `internal_volume_cm3` como `int`.
- Testes unitários cobrem todos os tipos inválidos e preservam determinismo.

### Dependências

- Nenhuma decisão de negócio nova.
- Deve preservar ADR-002 e o README do otimizador.

---

## [OC58] Definir e implementar verificação de prontidão do backend

- **Tipo:** melhoria operacional.
- **Responsável primário sugerido:** Desenvolvedor 1.
- **Apoio sugerido:** Desenvolvedor 4.
- **Prioridade:** baixa.

### Objetivo

Distinguir aplicação em execução de aplicação pronta para atender operações dependentes do banco.

### Comportamento atual

`CONFIRMADO`: `/health` permanece como liveness e retorna `ok` sem verificar
conexão com PostgreSQL ou estado das migrations.

`CONFIRMADO`: D11 foi aprovada em 2026-08-07 e registrada na `ADR-018`. A
ocorrência foi implementada conforme o contrato aprovado.

### Resultado

`CONFIRMADO`: `/ready` executa `SELECT 1` em conexão somente leitura, compara o
conjunto de revisões do banco com os heads Alembic entregues e aplica orçamento
total de 2 segundos. Falhas retornam `503 SERVICE_NOT_READY` sem detalhes
internos.

`CONFIRMADO`: o Compose usa `/ready` como healthcheck do backend sem aplicar
migrations automaticamente. O frontend preserva a inicialização independente do
estado saudável para não bloquear o bootstrap de um banco novo.

`CONFIRMADO`: a validação final aprovou Ruff, 894 testes do backend em PostgreSQL
16, 156 testes do frontend, ESLint, build de produção e smoke de queda e
recuperação do PostgreSQL. Durante a queda, `/health` permaneceu `200` e `/ready`
retornou `503`; após a recuperação, `/ready` voltou a `200`.

### Critérios de aceite

- `/health` mantém o contrato atual de liveness, salvo decisão explícita diferente.
- A rota e o contrato de readiness seguem `D11` e são documentados antes da implementação.
- Readiness falha quando o banco não está acessível.
- O comportamento para migration ausente ou desatualizada segue a decisão registrada.
- A verificação não altera dados e possui timeout curto.
- Compose e CI podem consumir a verificação aprovada.
- Testes cobrem banco disponível e indisponível.

### Dependências

- `D11` e `ADR-018`: caminho, payload, timeout e profundidade da verificação.
- Atualização de `docs/05-contratos-api.md` e documentação de infraestrutura.

---

## [OC59] Minimizar dados pessoais e paginar endpoints de listagem

- **Tipo:** segurança e contrato.
- **Responsáveis sugeridos:** Desenvolvedor 1 e Desenvolvedor 3.
- **Prioridade:** média.

### Objetivo

Evitar exposição desnecessária de dados pessoais e impedir listagens sem limite, preservando acesso detalhado apenas para perfis autorizados.

### Comportamento anterior

`CONFIRMADO`: endpoints de listagem retornam coleções completas sem paginação. Os mesmos schemas usados em detalhes podem expor e-mail, documento, telefone, CNH, endereço e observações.

### Decisão e divisão aprovada

`CONFIRMADO`: D12 foi aprovada em 2026-08-07 e registrada na `ADR-017`.

1. Registrar o contrato e a infraestrutura compartilhada de paginação.
2. Minimizar e paginar usuários, clientes, motoristas e pedidos.
3. Paginar caminhões e produtos e adaptar o consumidor frontend de caminhões.
4. Executar testes completos e encerrar a ocorrência na documentação.

### Resultado

`CONFIRMADO`: as seis coleções atualmente implementadas usam `COUNT`, `LIMIT` e
`OFFSET`, respeitam o limite máximo de 100 e retornam o envelope da ADR-017.
Usuários, clientes, motoristas e pedidos usam schemas resumidos; os endpoints de
detalhe mantêm os schemas completos protegidos pelo RBAC existente.

`CONFIRMADO`: o consumidor frontend de caminhões usa os metadados do backend e
oferece navegação entre páginas. A busca e o filtro continuam restritos à página
atual porque D12 não aprovou filtros server-side.

`CONFIRMADO`: a validação final executou 883 testes do backend sobre PostgreSQL
16, a suíte completa do frontend, Ruff, ESLint e build de produção.

### Critérios de aceite

- Campos retornados por listagens seguem a decisão `D12`.
- Dados pessoais são omitidos ou mascarados conforme recurso e perfil aprovado.
- Endpoints de detalhe preservam apenas os campos autorizados para o usuário atual.
- Paginação, ordenação e metadados seguem um contrato único documentado.
- Repositories aplicam limite no banco e não carregam toda a tabela para paginar em memória.
- Filtros não permitem enumeração indevida de dados pessoais.
- Frontend é atualizado junto com a mudança de contrato.
- Testes cobrem primeira página, limites, coleção vazia e campos sensíveis ausentes.

### Dependências

- `D12`: campos, mascaramento, paginação, ordenação e filtros.
- `OC51`: usuário autenticado e perfil disponível na autorização.
- Atualização coordenada de `docs/05-contratos-api.md` e schemas do frontend.

### Fora do escopo

- Busca externa, motor de pesquisa ou exportação massiva de dados.

---

## [OC60] Endurecer autenticação e substituir JWT por sessão revogável

- **Tipo:** segurança e contrato.
- **Responsável primário confirmado:** Desenvolvedor 1.
- **Prioridade:** alta.
- **Situação:** implementada e validada localmente em 2026-08-09.

### Objetivo

Remover credenciais do Web Storage, limitar tentativas de login, modernizar o
hash e disponibilizar sessão revogável com proteção CSRF para o frontend próprio.

### Critérios de aceite

- D18 e `ADR-020` registram o contrato antes da implementação.
- Novas senhas seguem a política de 15 a 128 caracteres e blocklist local.
- Argon2id usa m=19 MiB, t=2 e p=1; login válido migra PBKDF2 legado.
- Login limita conta e IP e retorna `429` com `Retry-After` durante bloqueio.
- `auth_sessions` guarda somente hash de identificador aleatório de 256 bits.
- Produção emite `__Host-loadx_session` com flags seguras; local HTTP usa cookie
  compatível explicitamente documentado.
- Sessão respeita 30 minutos inativos e 8 horas absolutas.
- Métodos inseguros validam origem; métodos autenticados validam
  `X-CSRF-Token`.
- `POST /auth/logout` revoga a sessão e limpa o cookie.
- Troca de senha, desativação e alteração de papel revogam todas as sessões do
  usuário.
- Frontend usa cookie, mantém CSRF somente em memória e não usa `localStorage`
  para autenticação.
- Migration real, downgrade, testes PostgreSQL, Ruff, frontend, build e scanners
  passam.

### Resultado

`CONFIRMADO`: a OC60 foi dividida em commits pequenos para decisão, senha,
throttling, persistência de sessão, contrato HTTP, revogação, frontend e headers
defensivos. O banco chegou à revisão `20260808_0006` exclusivamente por Alembic.

`CONFIRMADO`: a validação final executou 577 testes unitários/health e 351 testes
de integração em PostgreSQL 16, totalizando 928 testes de backend. O ciclo real
de migration executou `upgrade head`, `downgrade -1` e novo `upgrade head`.

`CONFIRMADO`: o frontend passou por ESLint, 159 testes e build. `pip-audit`,
`npm audit`, Bandit e a busca por padrões de credencial terminaram sem achados.
O Compose principal aplicou `20260808_0006`, deixou backend e banco saudáveis e
respondeu `/ready` com sucesso.

### Fora do escopo

- MFA, recuperação de senha, cofre de segredos, TLS do proxy, alertas externos e
  criação dos papéis PostgreSQL de produção.

`RISCO IDENTIFICADO`: MFA obrigatório sem fluxo de cadastro e recuperação pode
bloquear o único administrador; a implementação exige ocorrência própria.

---

## [OC61] Viabilizar runtime seguro de produção

- **Tipo:** segurança e infraestrutura.
- **Responsável primário confirmado:** Desenvolvedor 1.
- **Prioridade:** alta.
- **Situação:** implementada e validada localmente em 2026-08-09.

### Objetivo

Fornecer uma referência executável de produção para o frontend próprio com TLS,
proxy confiável, segredos montados e credenciais PostgreSQL segregadas, sem
escolher ou contratar provedor externo.

### Critérios de aceite

- Compose de produção não publica backend nem PostgreSQL diretamente.
- Caddy serve o build estático e encaminha API e sondas sob a mesma origem HTTPS.
- Uvicorn confia headers de proxy somente do IP privado fixo do Caddy.
- URLs de banco e `SECRET_KEY` chegam aos serviços por arquivos em
  `/run/secrets`.
- Migration e aplicação recebem credenciais PostgreSQL diferentes.
- O papel da aplicação não pode criar ou remover estruturas.
- CSP, HSTS e demais headers defensivos são preservados no frontend publicado.
- Configuração do Compose, Caddyfile, imagem estática e SQL de papéis são
  validados antes do encerramento.

### Resultado

`CONFIRMADO`: a referência isolada concluiu migration, manteve backend privado,
publicou apenas Caddy em 80/443, redirecionou HTTP e respondeu frontend,
`/health` e `/ready` por HTTPS. CSP, HSTS e headers defensivos foram observados;
a assinatura do servidor backend não foi exposta.

`CONFIRMADO`: o SQL permitiu DDL ao papel de migration e DML ao papel da
aplicação. A tentativa de criar tabela como `loadx_app` falhou por falta de
permissão, conforme o critério de menor privilégio.

`CONFIRMADO`: os eventos estruturados cobrem sucesso/falha de login, throttling,
criação, expiração e revogação de sessões e mudanças sensíveis de usuário. A
integração externa pode filtrar `alert=true` sem receber e-mail, IP ou segredo.

`CONFIRMADO`: a validação completa aprovou Ruff, 590 testes unitários/health e
351 testes em PostgreSQL 16, totalizando 941 testes de backend. ESLint, 159
testes do frontend, build, orçamento gzip, `pip-audit`, `npm audit` e Bandit
também passaram.

### Fora do escopo

- Contratação de domínio, cofre, banco gerenciado, observabilidade ou serviço de
  alertas.
- Alta disponibilidade, backup, restauração e deploy em uma plataforma real.
- MFA e recuperação de senha.

---

## [OC62] Definir MFA e recuperação segura de acesso

- **Tipo:** proposta de segurança e contrato.
- **Responsável primário recomendado:** Desenvolvedor 1.
- **Prioridade recomendada:** alta, antes da produção.
- **Situação:** `PENDENTE DE DEFINIÇÃO` e aprovação; nenhuma implementação foi
  iniciada.

### Objetivo proposto

Definir, antes de alterar banco ou API, o ciclo completo de MFA obrigatório para
`ADMIN` e `LOGISTICS_MANAGER` e a recuperação de acesso sem criar um caminho que
contorne o segundo fator.

### Decisões necessárias

- `DECISÃO NECESSÁRIA`: passkey/WebAuthn como fator principal com TOTP de
  contingência, ou TOTP como primeira entrega.
- `DECISÃO NECESSÁRIA`: cadastro, confirmação, substituição e remoção de fatores,
  incluindo reautenticação para cada ação sensível.
- `DECISÃO NECESSÁRIA`: quantidade, entrega, uso único e regeneração de códigos
  de recuperação, armazenados somente como hash.
- `DECISÃO NECESSÁRIA`: procedimento auditável para perda de dispositivo,
  recuperação de senha e administrador de emergência, sem bloquear o primeiro
  bootstrap nem permitir bypass permanente.
- `DECISÃO NECESSÁRIA`: modelo de dados, contratos HTTP, interface e eventos de
  auditoria que materializam essas escolhas.

### Recomendação para aprovação

`RECOMENDAÇÃO`: preferir passkeys, aceitar TOTP como contingência, fornecer
códigos de recuperação de uso único e exigir reautenticação para gerenciar
fatores. A ocorrência deve começar por ADR e threat model e só depois dividir
banco, serviço, API e frontend em commits testáveis.

### Fora do escopo da proposta

- Contratar provedor externo antes da escolha da plataforma de produção.
- Implementar recuperação baseada apenas em perguntas pessoais, suporte sem
  auditoria ou desativação silenciosa do MFA.

---

## Detalhamento da ocorrência existente OC09

## [OC09] Implementar controle de viagens e entregas

- **Tipo:** funcionalidade já prevista.
- **Responsável primário confirmado:** Desenvolvedor 1.
- **Responsabilidade compartilhada:** Desenvolvedor 4 para fluxo operacional, ocorrências e testes integrados.

### Objetivo refinado

Implementar persistência, serviços e contratos HTTP de viagens e entregas
vinculadas a plano aprovado, motorista e pedidos, exigindo carregamento
finalizado para iniciar e preservando histórico de status.

### Comportamento atual

`CONFIRMADO`: models, migration `20260809_0008`, repositories, services, rotas,
RBAC por objeto e histórico atômico estão implementados. A migration anterior
`20260809_0007` materializa o vínculo `users.driver_id` aprovado por D21. A
validação local cobre regras unitárias, rollback, OpenAPI, API e PostgreSQL 16.

### Critérios de aceite

- Models `Trip` e `Delivery` correspondem exatamente a `docs/03-modelo-dados.md`.
- Migration pequena cria `trips` e `deliveries` com PKs, FKs, uniques, índices e constraints aprovadas.
- Viagem referencia plano de carga existente e motorista ativo.
- Viagem só pode iniciar depois do carregamento finalizado.
- Entregas são vinculadas aos pedidos do plano sem acessar tabelas internas de outro módulo fora de services públicos.
- Transições seguem `D07` e a finalização da viagem segue `D08`.
- Toda mudança de status gera histórico na mesma transação, conforme padrão da `OC52`.
- Datas são persistidas em UTC.
- Endpoints correspondem a `docs/05-contratos-api.md`.
- Testes unitários cobrem regras e testes PostgreSQL cobrem repository, migration e API.
- GPS, roteirização externa, telemetria e mapas permanecem fora do escopo.

### Dependências e bloqueios

- `CONFIRMADO`: planejamento de carga persistido e aprovado.
- `PENDENTE DE DEFINIÇÃO`: carregamento implementado e finalizado para liberar
  a transição positiva `SCHEDULED -> IN_ROUTE` no runtime real.
- `CONFIRMADO`: `OC51` fornece autenticação e ator da mudança.
- `CONFIRMADO`: `OC52` fornece o padrão atômico de histórico.
- `CONFIRMADO`: D07 a D10 e D21 foram resolvidas por `ADR-022`.

`CONFIRMADO`: D07, D08, D09, D10 e D21 foram resolvidas em `ADR-022` antes da
implementação. Estados de exceção permanecem deliberadamente fora da OC09.
