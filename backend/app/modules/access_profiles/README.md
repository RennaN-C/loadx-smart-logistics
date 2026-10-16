# Perfis e permissões — OC112

`CONFIRMADO`: catálogo fechado em `catalog.py`, persistência em models/repository,
regras transacionais em service e API administrativa em router. ADR-040 registra
as decisões para revisão. Não há regras executáveis, SUPERADMIN ou tenant local.

## Contratos

Todos os endpoints exigem sessão, ADMIN e Origin/CSRF nas mutações:

| Método | Rota (prefixo /api/v1) | Resultado |
|---|---|---|
| GET | /access-profiles | Envelope paginado, incluindo perfis fixos protegidos |
| GET | /access-profiles/permissions | Catálogo real, rótulo, módulo e classificação |
| GET | /access-profiles/{id} | Detalhe de perfil personalizado, grants e user_count |
| POST | /access-profiles | 201, criação de perfil personalizado |
| PATCH | /access-profiles/{id} | Atualização completa dos campos editáveis + version |

POST: `name` (1–120), `description` (até 500, default vazio), `active` (default
true), `permissions` (até 64, default vazio). PATCH exige todos esses campos e
`version > 0`; arrays repetidos, desconhecidos/reservados e extras são 422.
Nome único sem distinção de caixa/normalização PostgreSQL. Nome fixo é reservado.
UUID é a identidade técnica; nome, e-mail e CNPJ não identificam organização.

A paginação mantém quatro projeções fixas primeiro, na ordem ADMIN, gerente,
conferente e motorista, e perfis personalizados por created_at/id (sort_order asc/desc, default desc).
A interface usa a ordem padrão. page/page_size usam
limites centrais; dados/grants de perfis são carregados somente para a página.
Não há listagem de usuários por perfil: `user_count` é contagem real; associação
é consultada/editada na OC86. Perfis fixos são consultáveis na coleção, sem
mutação por UUID e sem DELETE.

Erros públicos: 401 autenticação, 403 permissão, 404 PROFILE_NOT_FOUND,
409 PROFILE_VERSION_CONFLICT/PROFILE_IN_USE/PROFILE_NAME_RESERVED/PROFILE_CONFLICT,
422 validação. Falhas inesperadas não expõem dados internos.

## Associação e migração

`users.role` mantém os quatro valores existentes e admite CUSTOM somente com
`custom_profile_id` preenchido. Papel fixo exige perfil nulo. Vínculo DRIVER não
é concedido por perfil personalizado. Mudança de CUSTOM para papel fixo precisa
enviar `custom_profile_id: null`, explicitamente. Campo inválido/inativo retorna
409 USER_PROFILE_INVALID/USER_PROFILE_INACTIVE. Permissões enviadas pelo cliente
não são autoridade de acesso. A edição de conta permanece exclusivamente ADMIN.

Login/me e respostas detalhadas de usuário acrescentam `permissions`,
`custom_profile_id` e `custom_profile_name`. A coleção acrescenta somente os dois
campos de perfil, preservando resumo de identidade da OC86. Frontend consome a
projeção efetiva; não une grants ao papel gerencial. F5/login restauram pelo banco.

Backfill sem reclassificação: NULL preserva cada papel legado. Migration
20261016_0024 sobre 20261009_0023; sem OC98. Downgrade é recusado se houver usuário
CUSTOM ou histórico de perfil, para não descartar acesso/auditoria. Rollback
estrutural requer plano explícito de preservação desse histórico; não apaga dados.

## Transações e segurança

- Grants têm PK composta, FK para perfil e FK composta para catálogo delegável;
  CHECK delegable=true impede privilégios reservados também fora do service.
- Associação/perfil usam advisory lock transacional 112159. Edição de perfil
  bloqueia usuários em ordem de UUID, depois perfil e sessões. Associação revalida
  perfil ativo; alterações concorrentes de versão retornam 409.
- Autorizações CUSTOM releem usuário e perfil sob SHARE e revalidam revogação da
  sessão. Estado ativo e grants são consultados na operação; ausência nega.
- Alterar grants/estado revoga sessões afetadas no mesmo commit da auditoria.
  Alterar associação revoga mesmo sem mudar role=CUSTOM. Nome/descrição não
  revogam. Falha faz rollback de perfil, grants, sessões e auditoria.
- Desativar perfil com qualquer associação retorna 409, mesmo conta inativa.
  Não há exclusão física via HTTP. Último ADMIN mantém locks/regras da OC86.
- CHECKER conserva planos aprovados; DRIVER conserva escopo próprio e vínculo
  ativo. ADMIN não personifica esses atores nem ignora estados do domínio.
- Busca global consulta cada categoria somente com sua permissão; anexos,
  evidências e importação também mantêm validação de ator/recurso.
- Auditoria de perfil: PROFILE_CREATED/PROFILE_UPDATED, ACCESS_PROFILE e somente
  nomes de campos. Eventos de perfil/empresa são omitidos para gerente antes da
  paginação. Nenhuma senha/token ou conteúdo de grant arbitrário em logs.

## Catálogo e matriz

`CONFIRMADO`: gestão e leitura são independentes. Para um fluxo completo, conceda
as consultas necessárias (por exemplo planejamento precisa ler pedidos/caminhões;
criar viagem pela UI precisa consultar motoristas). Isso não concede poderes de
identidade ou ignora regras operacionais.

| Permissão | Descrição | Classificação | Delegável | ADMIN | Gerente | CHECKER | DRIVER |
|---|---|---|---|---|---|---|---|
| loadx.customers.read | Consultar clientes | delegable | sim | sim | sim | — | — |
| loadx.customers.manage | Gerenciar clientes | delegable | sim | sim | sim | — | — |
| loadx.products.read | Consultar produtos | delegable | sim | sim | sim | sim | — |
| loadx.products.manage | Gerenciar produtos | delegable | sim | sim | sim | — | — |
| loadx.trucks.read | Consultar caminhões e frota | delegable | sim | sim | sim | sim | — |
| loadx.trucks.manage | Gerenciar caminhões e frota | delegable | sim | sim | sim | — | — |
| loadx.drivers.read | Consultar motoristas | delegable | sim | sim | sim | — | — |
| loadx.drivers.manage | Gerenciar motoristas | delegable | sim | sim | sim | — | — |
| loadx.orders.read | Consultar pedidos | delegable | sim | sim | sim | sim | — |
| loadx.orders.manage | Gerenciar pedidos | delegable | sim | sim | sim | — | — |
| loadx.planning.read | Consultar planejamento | delegable | sim | sim | sim | sim | — |
| loadx.planning.create | Criar planejamento | delegable | sim | sim | sim | — | — |
| loadx.planning.approve | Aprovar planejamento | delegable | sim | sim | sim | — | — |
| loadx.loading.read | Consultar carregamento | delegable | sim | sim | sim | sim | — |
| loadx.loading.create | Criar carregamento | delegable | sim | sim | sim | — | — |
| loadx.loading.operate | Conferir carregamento | operational | sim | sim | — | sim | — |
| loadx.trips.read | Consultar viagens | delegable | sim | sim | sim | — | — |
| loadx.trips.manage | Gerenciar viagens | delegable | sim | sim | sim | — | — |
| loadx.deliveries.read | Consultar entregas | delegable | sim | sim | sim | — | — |
| loadx.deliveries.manage | Gerenciar entregas | delegable | sim | sim | sim | — | — |
| loadx.occurrences.read | Consultar ocorrências | delegable | sim | sim | sim | — | — |
| loadx.occurrences.manage | Gerenciar ocorrências | delegable | sim | sim | sim | — | — |
| loadx.reports.read | Consultar relatórios | delegable | sim | sim | sim | — | — |
| loadx.messages.manage | Gerenciar comunicação simulada | delegable | sim | sim | sim | — | — |
| loadx.audit.read | Consultar auditoria administrativa | reserved | não | sim | sim | — | — |
| loadx.users.manage | Administrar contas e credenciais | reserved | não | sim | — | — | — |
| loadx.profiles.manage | Administrar perfis e permissões | reserved | não | sim | — | — | — |
| loadx.settings.manage | Administrar configurações da empresa | reserved | não | sim | — | — | — |
| loadx.integrations.read | Consultar saúde das integrações | reserved | não | sim | — | — | — |
| loadx.imports.manage | Importar cadastros | non_delegable | não | sim | sim | — | — |
| loadx.trips.own | Operar viagens e entregas próprias | identity | não | — | — | — | sim |

`CONFIRMADO`: reserved significa não concedível a perfil personalizado; a
projeção legada do gerente preserva auditoria. Imports é não delegável nesta OC
porque envolve múltiplos cadastros/validações. trips.own é exclusivo da identidade
DRIVER, com vínculo real. loading.operate é delegável a operador autenticado,
sem atribuir o nome ou a identidade CHECKER nem ampliar a auditoria existente. Poder de plataforma não existe no catálogo.
