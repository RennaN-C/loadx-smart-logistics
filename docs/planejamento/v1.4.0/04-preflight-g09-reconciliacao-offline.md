# G09 — preparação da reconciliação offline

**Rastreabilidade:** [Issue #489](https://github.com/RennaN-C/loadx-smart-logistics/issues/489).
**Data:** 25/11/2026, America/Sao_Paulo.
**Estado:** **EM ANDAMENTO**, preparação local independente; isolamento G09 não concluído.

`CONFIRMADO`: inventário baseado em `origin/desenvolvimento` no commit
`2bef6071bf76053e2358f2f182097db59513b47c`. A presença de implementações em
branches de trabalho não altera essa base. Este recorte não cria migration,
não reserva revisão Alembic, não altera modelos/contratos HTTP, não acessa banco
ou arquivos operacionais e não habilita uma segunda empresa.

## Contrato e inventário confirmado

Fontes: [ownership aprovado](02-matriz-ownership-53-tabelas.md),
[backfill legado](03-plano-backfill-organizacao-legada.md),
[ADR-049](../../decisions/ADR-049-multiempresa-organizacoes-isolamento.md) e
[ADR-033](../../decisions/ADR-033-anexos-operacionais.md).

| Recurso atual | Campos/referências que precisam ser preservados | Evidência na base |
|---|---|---|
| `audit_events` | `id`, `event_type`, `entity_type`, `entity_id`, `actor_id`, `changed_fields`, `created_at` | `backend/app/modules/status_history/models.py`, classe `AuditEvent` |
| Serialização dos campos auditados | String com nomes de campos separados por vírgulas; não contém valores antigos/novos | `status_history/service.py`, `AuditService.stage_administrative_event` |
| Evento de criação de usuário | `active,driver_id,email,name,role`; perfil customizado não consta nessa lista | `users/service.py`, `persist_user_with_audit` |
| Preferências em eventos `USER_UPDATED` | `notification_preferences.SECURITY`, `.TRIPS`, `.OCCURRENCES` | `notifications/inbox_service.py`, atualização auditada de preferências |
| `operational_attachments` | `id`, quatro FKs nullable (`order_id`, `trip_id`, `delivery_id`, `occurrence_id`), `recorded_by`, `event_id`, `media_type`, `size_bytes`, `sha256`, `fingerprint`, `status`, `recorded_at`, `revoked_at`, `revoked_by` | `attachments/models.py` |
| Integridade de recurso de anexo | Exatamente uma das quatro FKs; referências usam RESTRICT | `attachments/models.py`, `exactly_one_resource` |
| Identidade de retry | Unicidade atual `(recorded_by,event_id)`; fingerprint inclui recurso e conteúdo original | `attachments/models.py`; `attachments/service.py`, registro de arquivo |
| Blob e download | Port recebe UUID; adapter local usa `<uuid.hex>.bin`; download lê pelo UUID do anexo e valida tamanho/checksum | `app/integrations/evidence_storage.py`; `attachments/service.py`, `download` |
| Revogação | Metadados e bytes confirmados preservados; estado e autoria de revogação impedem download | README de `attachments`, ADR-033 e serviço de revogação |

`CONFIRMADO`: o ownership aprovado determina escopos PLATFORM/ORGANIZATION,
`source_event_id` para a proveniência e clones de eventos mistos. A organização
do alvo deve vir da referência real, nunca ser deduzida apenas do ator.
São contratos para a evolução; os campos de escopo não existem no model de
auditoria da base examinada.

## Artefato independente e o que ele demonstra

`CONFIRMADO`: [verificador puro](../../../backend/scripts/g09_reconciliation.py)
recebe snapshots tipados em memória: auditoria antes/depois, anexos antes/depois
e manifesto explícito de recursos/memberships. Não importa `app`, settings,
ORM, engine, storage, rede ou leitura/escrita de arquivos. Os testes usam apenas
UUIDs e datas fictícios, nomes de campos e hashes sintéticos.

O verificador rejeita:

- IDs duplicados, origens inventadas, reutilização do ID de outro evento e perda do ID original;
- alteração do ator ou timestamp de um evento e perda/duplicação/invenção de campos entre suas projeções;
- escopos inválidos, alvo ausente ou de outra organização e ator sem membership contextual;
- campos desconhecidos de eventos USER, categorias de preferência desconhecidas ou campos de membership indevidamente classificados como identidade global;
- perda/adição de anexos, manifest incompleto ou mudança de qualquer metadado original;
- anexo sem recurso ou com mais de um recurso e ausência da membership do autor/revogador.

`CONFIRMADO`: a execução retorna somente contagens. Erros são códigos fixos;
não reproduzem dados de entrada. O mesmo ensaio retorna a mesma contagem e
não modifica os objetos fornecidos. A implementação não escolhe IDs dos clones.

`RISCO IDENTIFICADO`: a função verifica **preservação e referências**, com
validação conservadora das categorias de campos USER; não resolve alvos reais
nem comprova a classificação semântica completa. Um manifesto coerente pode representar
uma classificação incorreta ou um export incompleto. Portanto, seu resultado
não é aprovação de backfill nem evidência de isolamento seguro. Campos vazios
ou duplicados precisam de revisão explícita; o ensaio recusa projeções vazias.
Valores de perfil/membership que não constam no evento histórico exigem o
snapshot aprovado correspondente; não podem ser reconstruídos desse contador.

## Exemplo sintético de evento misto

`CONFIRMADO`: o teste `rehearsal()` representa um `USER_UPDATED` fictício com
`changed_fields=(email,role)`. A proposta de ensaio possui duas projeções:

| Projeção | ID e proveniência | Destino e escopo | Campos preservados |
|---|---|---|---|
| Identidade | Conserva ID original; `source_event_id` aponta para ele | `USER_IDENTITY`, UUID do usuário, PLATFORM sem organização | `email` |
| Membership | Novo UUID sintético; mesma origem | `MEMBERSHIP`, UUID real indicado pelo manifesto, ORGANIZATION A | `role` |

Ambas conservam ator/data. O teste remove campos, altera autoria e cruza
referências para comprovar rejeição. O anexo sintético aponta somente para um
pedido A; os testes também preservam a referência em caso de revogação.

`RECOMENDAÇÃO`: ampliar os ensaios antes do backfill definitivo para criação
de usuário com perfil customizado vindo do snapshot, preferências SECURITY e
operacionais, COMPANY_PROFILE remapeado, CNH global versus tipo documental
customizado, auditoria de importação/outbox e eventos desconhecidos em quarentena.
Essas transformações não são implementadas pelo verificador de preservação.

## Sequência de reconciliação antes de uma migration G09

1. Concluir e integrar o ownership de viagens/entregas (G07) e ocorrências/evidências/histórico (G08). Não antecipar FKs para contratos ainda instáveis.
2. Congelar inventário de entidades/campos/eventos; resolver explicitamente referências reais de membership/preferências e catálogo global reservado. Campos/eventos desconhecidos bloqueiam ativação e seguem quarentena, sem descarte.
3. Preparar ensaio PostgreSQL 16 exclusivo e fictício, com comparação independente de contagens, UUIDs, hashes e timestamps, antes/depois. Não solicitar nem versionar export de dados reais.
4. Classificar por `entity_type`/`changed_fields`; revisar partições, remapeamentos e origem dos clones. Preservar IDs originais e ligar cada clone à origem. Não inferir escopo pelo ator.
5. Aplicar o verificador somente como uma das verificações; reconciliar os totais separadamente contra o banco de ensaio para detectar export incompleto.
6. Testar triggers/constraints, append-only e rollback/downgrade no PostgreSQL, inclusive registros revogados, clones e relacionamentos cruzados. Não apagar histórico para permitir downgrade.
7. Testar autorização de listagem, download, revogação, links temporários se existirem e isolamento de storage. Verificar bytes reais sintéticos por tamanho/checksum, não apenas seus metadados.
8. Integrar após gates de CI/revisão e autorização aplicável. Toda alteração de banco remoto/deploy permanece uma etapa posterior autorizada.

`PENDENTE DE DEFINIÇÃO`: revisão Alembic G09 e desenho final da quarentena;
contratos físicos do split de preferências G10; estratégia de chave contextual
do storage preservando UUIDs/blobs legados; retenção, fornecedor e backups de
produção. Esta preparação não resolve essas decisões nem cria serviços externos.

## Validação reproduzível

De `backend`, com Python 3.12 e dependências existentes:

```powershell
python -m pytest -q tests/unit/test_g09_reconciliation.py
python -m ruff check scripts/g09_reconciliation.py tests/unit/test_g09_reconciliation.py
python -m ruff format --check scripts/g09_reconciliation.py tests/unit/test_g09_reconciliation.py
```

`CONFIRMADO`: testes exercitam exclusivamente os invariantes descritos; não
substituem PostgreSQL, migrations, auditoria semântica, autorização HTTP ou
homologação de storage. G09 permanece **PENDENTE** de implementação e integração.
