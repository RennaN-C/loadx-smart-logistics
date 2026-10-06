# Comandos externos — OC79

`CONFIRMADO`: fronteira interna de autenticação, autorização e idempotência da
Issue #122. Decisão proposta para revisão em [ADR-026](../../../../docs/decisions/ADR-026-seguranca-comandos-externos.md).
Não existe endpoint novo, fornecedor habilitado ou chave padrão.

## Composição e fronteira de confiança

`CONFIRMADO`: o adapter chama `ExternalCommandService.process(body, signature)`
com bytes originais. Configure no servidor, nunca a partir de campos do request:

- `session_factory`: fábrica de Sessions novas, dedicadas, ligadas ao PostgreSQL;
  em runtime use `SessionLocal`, sem transação de request anterior ou writes pendentes;
- `ExternalAuthenticator`: autentica antes do parsing e retorna `TrustedIntegration`
  com integration_id/capabilities controlados pelo servidor;
- `ExternalActorResolver`: resolve subject somente por vínculo previamente
  aprovado no servidor; `BoundExternalActorResolver` copia um mapa imutável
  `(integration_id, subject) -> UUID de usuário`. Não converte subject em user_id;
- `HmacExternalAuthenticator`: implementação genérica opcional, HMAC-SHA-256 sobre
  todos os bytes, assinatura hexadecimal minúscula de 64 caracteres, comparação
  constante, chave `SecretBytes` com ao menos 32 bytes e exclusiva por integração.
  Não reutilize chave de sessão, não habilite fallback ou integração sem assinatura.

`CONFIRMADO`: usuário é resolvido via service de users com lock compartilhado que
impede alteração de papel/atividade/vínculo durante a transação. DRIVER requer
motorista ativo/vinculado sob lock. ADMIN e CHECKER não operam viagens/entregas.
LOGISTICS_MANAGER e DRIVER continuam sujeitos à autorização por objeto do domínio.
Capability é restrição adicional da integração, nunca uma concessão ao usuário.

## Envelope versão 1

`CONFIRMADO`: JSON estrito, sem campos extras/chaves duplicadas; máximo 16 KiB.

| Campo | Contrato |
|---|---|
| version | inteiro 1; boolean/string recusados |
| event_id | identificador opaco, 1–128 caracteres `[A-Za-z0-9_.:-]` |
| subject | identificador autenticado a resolver, mesma restrição de tamanho/formato |
| command | START_TRIP / START_DELIVERY / FINISH_DELIVERY |
| target_id | UUID explícito de viagem para START_TRIP, de entrega para os demais |
| issued_at | datetime ISO-8601 com timezone |
| expires_at | datetime ISO-8601 com timezone, maior que issued_at, intervalo máximo 5 min |

`CONFIRMADO`: issued_at até 30 segundos no futuro é tolerado; no instante
expires_at o comando é expirado. Clock é UTC, injetável nos testes. A validade é
verificada antes do domínio e após esperas/execução; expiração durante execução
desfaz a transação. Não há autorização inferida de telefone, role ou permissions.

`CONFIRMADO`: catálogo reaproveita comandos do simulador e somente chama
`TripService.change_trip_status` / `change_delivery_status`, preservando regras
e histórico. ARRIVED equivale a START_DELIVERY antes da assinatura. STATUS e
NEXT_DELIVERY são consultas e não passam por este registro de comandos mutáveis.
Não registra ocorrência, evidência, mídia ou notificação real nesta OC.

## Idempotência e transação

`CONFIRMADO`: primeira execução retorna `{id: UUID, duplicate: false}`; reenvio
válido retorna o mesmo id e duplicate true, sem chamar o domínio. A resposta não
contém payload ou dados de usuário. Mesmo reenvio exige autenticidade, capability,
ator atualmente autorizado e validade. Bytes diferentes (até espaços/ordenação
JSON), novo target/validade ou outro ator para a mesma identidade são conflito.
Reutilize exatamente os bytes assinados; novo evento requer novo event_id.

`CONFIRMADO`: PostgreSQL UNIQUE + INSERT ON CONFLICT serializam dois eventos
iguais; um executa e outro observa a confirmação. Se o primeiro falhar, sua
transação é desfeita e o segundo pode executar dentro da validade. Não há estado
intermediário confirmado nem fila/outbox. Linhas incompletas inesperadas falham
fechadas. Namespace por integration_id permite event_id igual em integrações
distintas. Registros não são apagados automaticamente.

`CONFIRMADO`: o service possui transação externa e Session separada na mesma
Connection com savepoints. Commits dos services existentes não confirmam o
registro externo; erro inclusive após commit interno desfaz registro, operação
e histórico. Não injete provider de notificação nem IO de rede nessa transação.
Envio de resposta/notificação ocorre depois da confirmação; falha posterior não
reexecuta domínio. OC109 definirá confiabilidade de efeitos externos.

## Erros e rastreabilidade

`CONFIRMADO`: `ExternalCommandError.code` é o contrato; adapters devem usar apenas
o código para resposta/log, sem exception cause/context/traceback/payload.

| Código | Significado | Mapeamento HTTP recomendado para adapter futuro |
|---|---|---:|
| EXTERNAL_AUTHENTICITY_INVALID | assinatura/autenticidade inválida | 401 |
| EXTERNAL_PAYLOAD_INVALID | estrutura, chave ou validade estrutural inválida | 422 |
| EXTERNAL_COMMAND_EXPIRED | prazo expirado | 410 |
| EXTERNAL_COMMAND_NOT_YET_VALID | emissão além da tolerância futura | 422 |
| EXTERNAL_COMMAND_FORBIDDEN | capability, binding, ator ou objeto negado | 403 |
| EXTERNAL_IDENTITY_CONFLICT | mesma identidade com bytes/ator incompatíveis | 409 |
| EXTERNAL_DOMAIN_REJECTED | recurso ausente ou estado/regra impedem comando | 409 |
| EXTERNAL_PROCESSING_FAILED | falha inesperada, rollback aplicado | 500 |

`RECOMENDAÇÃO`: a coluna HTTP orienta futuras OCs; não cria rota ou contrato HTTP
novo. Logs `loadx.security` têm correlation_id gerado pelo servidor, command_id
do receipt e resultado/código. Nunca incluem subject, event_id, body, assinatura,
chave, telefone ou mensagem de exception. Persistência armazena hashes/metadados.

## Validação

`CONFIRMADO`: em backend, com TEST_DATABASE_URL no PostgreSQL 16 exclusivo:

```bash
python -m pytest -q tests/unit/test_external_command_contract.py tests/unit/test_external_command_validation.py tests/integration/test_external_commands.py
```

`PENDENTE DE DEFINIÇÃO`: gestão de chaves e bindings, autenticação do fornecedor,
recepção HTTP (OC82/OC83), envio real (OC84) e retenção/reprocessamento (OC109).
Essas OCs precisam preservar esta fronteira, sessões/CSRF do frontend e RBAC.
