# Notificações operacionais

Serviço pequeno para transformar fatos operacionais já confirmados em mensagens
determinísticas enviadas por `WhatsAppProvider`.

`CONFIRMADO`: os gatilhos do MVP são início efetivo da viagem pelo endpoint HTTP
e registro efetivo de ocorrência. O destinatário é o telefone do motorista
vinculado à viagem.

`CONFIRMADO`: o envio ocorre depois do commit e é best-effort. Falha do provider
ou destinatário ausente não altera estados, não desfaz a operação e não cria
integração externa real.

`CONFIRMADO`: o ambiente atual usa somente `MockWhatsAppProvider`. Webhook,
WhatsApp real, upload de mídia e serviços pagos permanecem fora do MVP.

## OC84 — diagnóstico e proposta para revisão

`CONFIRMADO`: na base `desenvolvimento` `c9b634c`, o módulo contém somente o
service best-effort e não tem model, repository ou migration. As listas do mock
são voláteis, e `True` no service significa somente retorno local normal.
O histórico de viagem e o UUID de ocorrência são reutilizáveis como identidade
do fato, mas não substituem um registro de notificação ou de tentativa.

`CONFIRMADO`: o PR #223 (OC83) foi inspecionado em 20/10/2026 UTC: aberto em
draft, não integrado. Esta branch parte de `desenvolvimento`, sem copiar ou
exigir código desse PR. A OC79 integrada já fornece a fronteira reutilizável
para compatibilidade futura com HTTP inbound.

`RECOMENDAÇÃO`: o modelo mínimo de `operational_notifications`, seus campos,
FKs, CHECKs e unicidades estão em
[docs/03](../../../../docs/03-modelo-dados.md#oc84--proposta-de-notificações-operacionais-aguarda-revisão).
O fluxo transacional e o significado dos resultados mock estão em
[docs/04](../../../../docs/04-regras-negocio.md#oc84--contrato-proposto-e-limite-de-execução).
Essas propostas não criam persistência nem autorizam novos eventos ou públicos.

| Fato existente | Origem proposta | Destinatário operacional existente |
| --- | --- | --- |
| Início efetivo `SCHEDULED -> IN_ROUTE` | UUID de `status_history` da transição | Motorista da viagem |
| Registro de ocorrência | UUID da ocorrência | Motorista da viagem |

`SUPOSIÇÃO TÉCNICA`: uma linha por fato/tipo/motorista, protegida por índices
UNIQUE no PostgreSQL, é suficiente para a notificação lógica inicial. Não há
necessidade de copiar conteúdo ou telefone, nem introduzir broker/fila externa.

`PENDENTE DE DEFINIÇÃO`: revisão de Rennan para schema, estados mock e
destinatário operacional sem conta vinculada. A OC103 precisará definir o
vínculo de destinatários internos e acesso por objeto usando permissões atuais;
um UUID de motorista armazenado não concede direitos ao usuário. Não criar
rotas para CHECKER/DRIVER enumerarem dados alheios nem notificações arbitrárias.

`RISCO IDENTIFICADO`: os commits atuais dos services podem ser savepoints sob
uma transação externa (OC79 e fixtures). Não generalizar o envio após
`Session.commit()` como confirmação durável. A OC79 atualmente não injeta o
provider, preservando a ausência de IO antes de confirmar o comando. A evolução
deve registrar fato/notificação atomicamente e simular somente depois do commit
externo; exige testes com Sessions ligadas ao Engine e conexões independentes.

`RECOMENDAÇÃO`: após aprovação, alterar `notifications` (model/repository/service),
integração pública dos services de deliveries/occurrences, composição transacional
da OC79 e migration Alembic. Cobrir rollback, falha de persistência, duplicidade
concorrente, replay, origem correta, reinício, ausência de destinatário e mock
falho. Manter testes HTTP de 401/403, privacidade, GET sem efeitos e regressões.

`CONFIRMADO`: a saída permanece exclusivamente mock. Somente #193 pode aprovar
Meta na pré-produção. A central/UI é OC103; outbox, recuperação de pendências,
retries/backoff e reprocessamento são OC109. Nenhuma dessas capacidades pode
ser apresentada como implementada pela proposta.
