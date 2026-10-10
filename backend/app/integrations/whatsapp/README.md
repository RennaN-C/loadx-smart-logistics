# WhatsApp — mock na OC82

`CONFIRMADO`: nesta etapa, por orientação do solicitante em 09/10/2026,
o WhatsApp permanece exclusivamente mock. Não há adapter Meta, comunicação
externa, credenciais ou opção de ativação real. Decisão em
[ADR-036](../../../../docs/decisions/ADR-036-whatsapp-mock.md).

## Interface e configuração

`CONFIRMADO`: `WhatsAppProvider` mantém `receive_message` e `send_response` com
DTOs independentes do fornecedor. `get_whatsapp_provider` retorna o mock
compartilhado; desenvolvimento e testes podem instanciar `MockWhatsAppProvider`.
`WHATSAPP_PROVIDER=mock` é o padrão e o único valor aceito em `Settings`.
Valores diferentes são rejeitados na inicialização, inclusive em produção.

`CONFIRMADO`: o mock armazena mensagens recebidas e enviadas em listas do
processo e retorna a mesma mensagem. Não persiste envios entre reinicializações
nem comprova aceitação, entrega ou leitura pelo WhatsApp. `sent_at` representa o
horário UTC de criação do DTO. Telefone e conteúdo são omitidos de `repr`.

## Fluxo e segurança

`CONFIRMADO`: o provider não executa comandos de domínio nem acessa o banco.
`POST /api/v1/messages/interpret` continua um simulador interno com sessão,
Origin/CSRF e RBAC `ADMIN`/`LOGISTICS_MANAGER`. Telefone informado no simulador
não autentica um remetente externo. Regras de viagem e entrega são preservadas.

`CONFIRMADO`: notificações existentes usam o mock após o commit do domínio.
Falha do provider não desfaz uma operação confirmada; repetir o mesmo status
não produz nova transição nem novo aviso. A observabilidade existente registra
`NOTIFICATION_FAILED` sem conteúdo ou telefone.

`CONFIRMADO`: OC79 autentica, autoriza e deduplica comandos de domínio;
sua persistência não constitui histórico ou garantia de idempotência de envio.
O mock mantém o comportamento existente: chamadas explícitas repetidas a
`send_response` acrescentam mensagens à lista; não há retry automático.

## Testes e evolução

`CONFIRMADO`: na pasta `backend`, sem credenciais ou API externa:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest -q tests/unit/test_whatsapp_provider.py tests/unit/test_config.py
```

`CONFIRMADO`: testes `test_messages_api.py` e `test_notifications_api.py` de
integração cobrem sessão/RBAC, comandos, notificações e preservação do commit
em falhas. Exigem PostgreSQL conforme `tests/integration/README.md` e rodam na CI.

`PENDENTE DE DEFINIÇÃO`: a integração real da OC82 está adiada, não concluída.
Antes de retomá-la, definir fornecedor/API aprovado, credenciais exclusivamente
por ambiente, contrato de retorno/erros, timeouts, retries seguros e idempotência
de saída. Recepção/webhook pertence à OC83; notificações reais à OC84;
persistência/outbox e reprocessamento à OC109. Não há escolha de fornecedor,
template ou modelo novo aprovada nesta revisão.
