# Ocorrências propostas para o backend

## Estado deste documento

`RECOMENDAÇÃO`: este documento reúne ocorrências prontas para serem copiadas para o GitHub Projects após revisão da equipe.

`RISCO IDENTIFICADO`: a sequência oficial atual termina em `OC48`. Os identificadores `OC49` a `OC59` são sugestões e devem ser confirmados antes da abertura das issues para evitar conflito com ocorrências criadas em paralelo.

`CONFIRMADO`: nenhuma ocorrência abaixo está aprovada apenas por constar neste documento. Cada uma deve receber responsável, revisão de escopo e aceite da equipe antes da implementação.

## Resumo de prioridade

| Identificador sugerido | Prioridade | Responsável primário sugerido | Situação |
|---|---|---|---|
| `OC49` | Alta | Desenvolvedor 1 | Implementada localmente; pendente de PR e revisão |
| `OC50` | Alta | Desenvolvedor 1 | Implementada localmente; pendente de PR e revisão |
| `OC51` | Alta | Desenvolvedor 1 | Desbloqueada por `D01`, `D02` e `D03`; pronta para implementação |
| `OC52` | Alta | Desenvolvedor 1 | Bloqueada por `D04` e `D05` |
| `OC53` | Alta | Desenvolvedor 1, com revisão do Desenvolvedor 4 | Pronta para aprovação |
| `OC54` | Média | Desenvolvedor 4, com apoio do Desenvolvedor 1 | Pronta para aprovação |
| `OC55` | Média | Desenvolvedor 1, com revisão do Desenvolvedor 4 | Pronta para aprovação |
| `OC56` | Média | Desenvolvedor 1 e Desenvolvedor 3 | Bloqueada por `D06` |
| `OC57` | Média | Desenvolvedor 2 | Pronta para aprovação |
| `OC58` | Baixa | Desenvolvedor 1, com apoio do Desenvolvedor 4 | Bloqueada por `D11` |
| `OC59` | Média | Desenvolvedor 1 e Desenvolvedor 3 | Bloqueada por `D12` |

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

`CONFIRMADO`: após a `OC51-E`, `/auth/me`, usuários, clientes e motoristas validam token e aplicam a matriz aprovada; `/auth/register` não existe mais. Caminhões, produtos e pedidos ainda aguardam as próximas partes da ocorrência.

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

`CONFIRMADO`: pedidos podem trocar de status sem gravar `status_history`. O service de histórico executa `commit()` próprio, o que impede composição transacional segura.

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

`CONFIRMADO`: os testes de integração usam SQLite em memória e `Base.metadata.create_all`, sem aplicar as migrations oficiais.

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
- Migrations `20260729_0001` a `20260730_0003`.

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

`CONFIRMADO`: fixtures repetem criação de engine e cliente, não executam `engine.dispose()` e não usam `TestClient` como context manager. `ruff format --check` indica arquivos fora do padrão.

### Critérios de aceite

- Fixtures compartilhadas ficam em `conftest.py` no menor escopo coerente.
- `TestClient` é fechado ao final dos testes.
- Sessions, conexões e engines são encerradas e descartadas.
- A suíte não emite `ResourceWarning` causado pelo código de teste.
- `ruff check .` e `ruff format --check .` passam.
- A mudança de formatação não altera contratos ou regras de negócio.
- Os 225 cenários existentes continuam passando, além dos testes adicionados pelas demais ocorrências.

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

`CONFIRMADO`: o backend responde pesos como strings, enquanto os exemplos de `docs/05-contratos-api.md` usam números JSON.

### Critérios de aceite

- A equipe registra a decisão `D06`.
- Schemas de entrada, schemas de saída e OpenAPI usam a representação aprovada.
- Documentação e exemplos usam a mesma representação.
- O frontend consome o valor sem conversão implícita ou perda silenciosa de precisão.
- Testes de contrato verificam valor e tipo JSON.
- Caminhões, produtos, pedidos futuros, planos e relatórios seguem a mesma convenção.

### Dependências

- `D06`: número JSON ou string decimal.
- Revisão conjunta entre backend e frontend.

---

## [OC57] Rejeitar tipos inválidos no cálculo de capacidade do caminhão

- **Tipo:** correção de domínio.
- **Responsável primário sugerido:** Desenvolvedor 2.
- **Prioridade:** média.

### Objetivo

Garantir que dimensões do cálculo de capacidade sejam inteiros positivos e que o resultado `internal_volume_cm3` permaneça inteiro.

### Comportamento atual

`CONFIRMADO`: `calculate_truck_capacity` aceita `bool` e `float` positivos nas dimensões; um `float` produz volume com tipo incompatível com o contrato.

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

`CONFIRMADO`: `/health` retorna `ok` sem verificar conexão com PostgreSQL ou estado das migrations.

### Critérios de aceite

- `/health` mantém o contrato atual de liveness, salvo decisão explícita diferente.
- A rota e o contrato de readiness seguem `D11` e são documentados antes da implementação.
- Readiness falha quando o banco não está acessível.
- O comportamento para migration ausente ou desatualizada segue a decisão registrada.
- A verificação não altera dados e possui timeout curto.
- Compose e CI podem consumir a verificação aprovada.
- Testes cobrem banco disponível e indisponível.

### Dependências

- `D11`: caminho, payload e profundidade da verificação.
- Atualização de `docs/05-contratos-api.md` e documentação de infraestrutura.

---

## [OC59] Minimizar dados pessoais e paginar endpoints de listagem

- **Tipo:** segurança e contrato.
- **Responsáveis sugeridos:** Desenvolvedor 1 e Desenvolvedor 3.
- **Prioridade:** média.

### Objetivo

Evitar exposição desnecessária de dados pessoais e impedir listagens sem limite, preservando acesso detalhado apenas para perfis autorizados.

### Comportamento atual

`CONFIRMADO`: endpoints de listagem retornam coleções completas sem paginação. Os mesmos schemas usados em detalhes podem expor e-mail, documento, telefone, CNH, endereço e observações.

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

## Detalhamento da ocorrência existente OC09

## [OC09] Implementar controle de viagens e entregas

- **Tipo:** funcionalidade já prevista.
- **Responsável primário confirmado:** Desenvolvedor 1.
- **Responsabilidade compartilhada:** Desenvolvedor 4 para fluxo operacional, ocorrências e testes integrados.

### Objetivo refinado

Implementar persistência, serviços e contratos HTTP de viagens e entregas vinculadas a plano carregado, motorista e pedidos, preservando histórico de status.

### Critérios de aceite propostos

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

- Planejamento de carga persistido e aprovado.
- Carregamento implementado e finalizado.
- `OC51` para autenticação e ator da mudança.
- `OC52` para padrão atômico de histórico.
- `D07`: estados e transições de viagem/entrega.
- `D08`: regra de finalização com entregas problemáticas.
- `D09`: tratamento de divergência de carregamento.
- `D10`: entidades auditáveis e consulta de histórico.

`RISCO IDENTIFICADO`: iniciar models ou migration da `OC09` antes dessas decisões pode criar estados e regras não aprovados.
