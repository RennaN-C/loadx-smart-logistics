# Migrations

O Alembic versiona toda alteração estrutural do PostgreSQL.

## Arquivos oficiais

- `alembic.ini`: configuração principal do Alembic.
- `migrations/env.py`: carrega `settings.database_url` e `Base.metadata`.
- `migrations/script.py.mako`: template das revisions.
- `migrations/versions`: migrations versionadas.

`CONFIRMADO`: o head atual é `20261020_0027` (OC90), após `20261020_0026`
(OC103) e `20261020_0025` (OC84). Historicamente OC105 sucede OC87
`20261007_0015` e evidências OC80 `20261007_0014`. A OC87 cria necessidade/partes/claims e triggers de integridade
diferidas; downgrade remove esses registros/triggers e tipos de histórico próprios.
A revisão `20260830_0011` adiciona
`trips.created_at` para ordenação determinística e sucede as migrations de
ocorrências e carregamento. `20260809_0007` vincula usuários a motoristas;
`20260809_0008` fecha o catálogo auditável e cria `trips` e `deliveries`. As
revisões anteriores da OC60 criam `auth_login_throttles`, sem e-mail ou IP
brutos, e `auth_sessions`, que persiste somente o hash do identificador opaco.

## Comandos

Execute a partir da pasta `backend`:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic downgrade -1
```

Com Docker Compose, a partir da raiz:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
```

`CONFIRMADO`: `docker compose up` executa automaticamente `alembic upgrade
head` no serviço one-shot `migrate`. O backend só inicia se esse serviço terminar
com sucesso; `/ready` apenas confere o resultado e não altera o banco.

## Regras

- Nunca envie somente um SQL solto.
- Nunca altere o staging manualmente como solução definitiva.
- A migration deve subir junto com models, testes e atualização do modelo de dados.
- Revise `upgrade()` e `downgrade()` antes de abrir PR.
- Use dados fictícios em seeds e testes.

`CONFIRMADO` (OC105): head `20261008_0016` → down_revision `20261007_0015`.
Adiciona `active` com default true a clientes/produtos e expande o catálogo
restrito de auditoria. Upgrade preserva UUIDs, documentos, códigos e todas as
FKs. Downgrade **não** apaga eventos de auditoria nem reativa cadastros
silenciosamente: é bloqueado se houver clientes/produtos arquivados ou qualquer
evento específico de ciclo de vida da OC105. Somente é permitido quando não
existe estado ou auditoria OC105 a preservar. Para reverter após uso real,
planeje migração compensatória com preservação de dados; não remova registros
de auditoria para forçar o downgrade.

## OC99 — revision 20261008_0017

`CONFIRMADO`: encadeada a `20261008_0016`, cria customer_addresses, constraints
e índices e adiciona proveniência/snapshot aos pedidos. Backfill cria um
principal por cliente, inclusive arquivados, sem alterar o estado do cliente.
Pedidos antigos preservam seu próprio texto; vínculo com endereço não é
inferido. A suíte PostgreSQL 16 verifica dados legados, upgrade, downgrade,
novo upgrade, alembic check e único head.

`CONFIRMADO`: downgrade é permitido para backfill intocado e bloqueia qualquer
endereço novo/editado/arquivado, proveniência/snapshot estruturado ou auditoria
de endereços que seria perdido. Falha transacional preserva o schema e dados.
Não remova dados de produção para contornar essa proteção.

## OC100 — revision 20261009_0018

`CONFIRMADO`: head único encadeado a 20261008_0017. Acrescenta campos opcionais
de odômetro/revisão em trucks, histórico truck_maintenances com FK RESTRICT,
CHECKs de tipo/período/valores não negativos e índice de histórico/período;
expande o catálogo de auditoria. Dados antigos mantêm quilometragem desconhecida,
sem histórico artificial. Upgrade/downgrade seguro preserva OC99/OC105;
uso da OC100 bloqueia downgrade que perderia histórico, km/revisão ou auditoria.

## OC101 — revision 20261009_0019

`CONFIRMADO`: segue 20261009_0018; adiciona documentos com índice único parcial
de versão corrente, políticas com unique por caminhão/tipo e catálogos de
auditoria. Sem backfill de obrigatoriedade/validade e sem mudança em dados
existentes. Downgrade sem dados é reversível; com documentos/políticas/auditoria
OC101 é bloqueado para preservar histórico. Testes usam PostgreSQL 16 real e
validam upgrade/downgrade/head e constraints.

## OC102 — revision 20261009_0020

`CONFIRMADO`: down_revision 20261009_0019, único head. Adiciona validade opcional
a drivers, tipos aprovados (CNH nativo), versões documentais e políticas com
índice único parcial, FK RESTRICT e CHECKs. Backfill de número/categoria dos
legados sem inventar validade; flags de backfill permitem downgrade intocado.
Histórico novo, políticas, validade e auditoria OC102 bloqueiam downgrade para
não descartar dados. Testes PostgreSQL 16 cobrem backfill legado, upgrade,
downgrade, constraints, concorrência e rollback.


## OC103 — revision 20261020_0026

`CONFIRMADO`: revisão sobre 20261020_0025. Acrescenta destinatários internos,
primeira leitura e preferências, sem alterar operational_notifications. Backfill
associa fatos reais às contas elegíveis no corte, sem destinatários históricos
inferidos. FK/PK/índices/CHECK e trigger protegem isolamento estrutural, segurança
obrigatória e identidade/primeira leitura imutáveis. Com qualquer associação ou
preferência, downgrade é recusado: preservar dados e planejar migração compensatória.
A suíte percorre upgrade/downgrade/upgrade e testa backfill e recusa após uso.


## OC90 — revision 20261020_0027

`CONFIRMADO`: head único após 20261020_0026 (OC103). Acrescenta FK opcional de
Delivery para parte, UNIQUE parte/pedido e índice único parcial por pedido legado.
Triggers protegem contexto operacional e imutabilidade dos vínculos/partição.
Backfill associa entregas existentes de distribuição com uma parte; entregas
legadas continuam NULL. Não há exclusão nem reescrita de históricos.

Upgrade/downgrade/novo upgrade e alembic check são exercitados no PostgreSQL 16.
Downgrade falha antes de DDL se houver entrega com parte, inclusive uma única:
o runtime anterior não suporta a semântica operacional multi. Preservar contexto
e auditoria; usar migration compensatória. Não apagar dados para contornar.

`CONFIRMADO` (OC90): upgrade revalida entregas antigas com a mesma trigger de
contexto usada por escritas futuras. Vínculo antigo inconsistente aborta o upgrade
transacional, preservando schema/dados anteriores; não há correção silenciosa.

`CONFIRMADO`: esta mesma migration OC90, ainda não integrada, foi renumerada para
0027 ao atualizar a base: 0025/0026 já pertencem a OC84/OC103 em desenvolvimento.
Não é criada uma segunda revisão OC90. A guarda `protect_operated_load_plan()`
congela linhas inteiras de planos e seus pedidos/itens desde LoadingSession ou
Trip, inclusive legado; no-op permanece permitido. Pais em UUID crescente com
NOWAIT evitam espera invertida filho/pai durante criação de checklist. Contenção
rejeita com `ck_load_plans__operational_snapshot` e exige retry da transação.
Downgrade permitido remove os três triggers `protect_operated_load_*` e a função;
o bloqueio fail-safe por entregas de parte ocorre antes de qualquer remoção.
