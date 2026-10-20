# Emissor local de homologação — OC83

`CONFIRMADO`: execute a partir de backend com Python 3.12 e dependências do lock.
`emit_inbound.py` cria um evento v1 em arquivo novo, assina seus bytes exatos e
faz POST HTTP real. Arquivo existente é reutilizado sem mudar event_id, bytes ou
validade. A chave vem exclusivamente do ambiente, nunca de argumento/arquivo de
evento. O emissor usa somente 127.0.0.1, com porta inteira de 1 a 65535 (--port, padrão 8000). Não aceita URL/host e recusa redirects.
Saída contém apenas status HTTP e receipt técnico; não imprime corpo/assinatura.

## Preparar ambiente local

`CONFIRMADO`: use dados fictícios e banco de desenvolvimento local com migrations.
Crie usuário operacional ativo pelo fluxo aprovado e obtenha UUID de viagem
SCHEDULED com carregamento FINISHED, ou entrega em estado apropriado. O binding
é definido pelo operador e não pode ser criado pelo payload recebido.

PowerShell, no terminal do backend (não registrar valores reais no histórico):

```powershell
$env:APP_ENV = 'local'
# DATABASE_URL já deve estar disponível pelo ambiente seguro local.
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$env:INBOUND_WEBHOOK_SIGNING_KEY = [Convert]::ToBase64String($bytes)
$rng.Dispose()
$env:INBOUND_WEBHOOK_ENABLED = 'true'
$actorId = Read-Host 'UUID do usuário fictício autorizado'
$env:INBOUND_WEBHOOK_BINDINGS = @{ 'emissor-local' = $actorId } | ConvertTo-Json -Compress
$env:INBOUND_WEBHOOK_CAPABILITIES = '["START_TRIP","START_DELIVERY","FINISH_DELIVERY"]'
# Instalar pelo lock se necessário; aplicar migrations ao banco local.
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

`CONFIRMADO`: o emissor precisa herdar as MESMAS variáveis; abra outro terminal
pelo gerenciador local que compartilhe o ambiente seguro. Não gere outra chave
no terminal do emissor; não copie a chave para chat, Git, argumentos ou logs.

No terminal do emissor, ainda em backend:

```powershell
$eventFile = Join-Path $env:TEMP ('loadx-event-' + [Guid]::NewGuid() + '.json')
$tripId = Read-Host 'UUID da viagem fictícia SCHEDULED com carga finalizada'
python scripts/emit_inbound.py --event-file $eventFile --subject emissor-local --command START_TRIP --target-id $tripId
# Mesmo arquivo/assinatura: mesmo receipt, duplicate=true.
python scripts/emit_inbound.py --event-file $eventFile
# Assinatura inválida: 401 e nenhuma alteração.
python scripts/emit_inbound.py --event-file $eventFile --invalid-signature --expected-status 401
# Nova intenção START_DELIVERY sobre entrega já DELIVERED: 409.
$invalidStateEvent = Join-Path $env:TEMP ('loadx-event-' + [Guid]::NewGuid() + '.json')
$deliveredId = Read-Host 'UUID de entrega fictícia já concluída'
python scripts/emit_inbound.py --event-file $invalidStateEvent --subject emissor-local --command START_DELIVERY --target-id $deliveredId --expected-status 409
```

`CONFIRMADO`: pode interromper/reiniciar o backend com a mesma configuração e
reenviar o primeiro arquivo dentro dos 4 minutos gerados pelo harness. Receipt
continua o mesmo: deduplicação é PostgreSQL, não memória. Após validade, esperar
410 (`--expected-status 410`); não estender validade mantendo event_id já aceito.
JSON criado tem IDs e timestamps fictícios, sem chave; remover arquivos locais
após homologação e nunca versioná-los. Não testar contra produção.

## Verificação automatizada completa

`CONFIRMADO`: na raiz, iniciar PostgreSQL 16 exclusivo de testes:

```powershell
docker compose -p loadx-tests -f compose.test.yaml up -d --wait
$env:TEST_DATABASE_URL = 'postgresql+psycopg://loadx_test:loadx_test_local@127.0.0.1:55432/loadx_test'
Set-Location backend
# Desabilitar flags manuais: as fixtures preparam runtime isolado.
$env:INBOUND_WEBHOOK_ENABLED = 'false'
python -m pytest -q tests/integration/test_inbound_webhook_live.py
python -m pytest -q tests/unit/test_inbound_webhook.py tests/integration/test_inbound_webhook_http.py tests/integration/test_external_commands.py
python -m ruff check .
python -m ruff format --check .
```

`CONFIRMADO`: test_inbound_webhook_live.py gera chave aleatória efêmera, inicia
Uvicorn real em loopback, cria/assina evento com este emissor, confirma sucesso,
assinatura inválida, idempotência e estado rejeitado, reinicia processo e verifica
receipt, efeito e histórico únicos no PostgreSQL. Subprocessos são encerrados.
Fixtures exigem loadx_test distinto do banco da aplicação e recriam seu schema;
nunca apontar TEST_DATABASE_URL para banco de desenvolvimento/produção.

`CONFIRMADO`: mídia inbound está bloqueada; não fornece upload, storage ou Meta.
Contrato completo: ../app/modules/messages/inbound.md.
