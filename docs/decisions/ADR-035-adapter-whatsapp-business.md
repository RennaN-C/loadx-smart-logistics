# ADR-035: manter WhatsApp exclusivamente mock nesta etapa — OC82

Status: aceita para o escopo mock por orientação do solicitante em 09/10/2026;
a integração real permanece adiada

## Contexto

`CONFIRMADO`: a Issue #125 descreve a evolução para um adapter real substituível.
O solicitante definiu que a implementação Meta não é necessária agora e que o
projeto deve manter o mock. Esta decisão restringe a entrega atual e não declara
concluídos os critérios de integração real da OC82.

## Decisão

`CONFIRMADO`: manter a port `WhatsAppProvider`, DTOs existentes e
`MockWhatsAppProvider` compartilhado, sem IO externo. `WHATSAPP_PROVIDER` aceita
somente `mock`; configuração diferente é rejeitada na inicialização.

`CONFIRMADO`: remover a implementação Meta e suas configurações de credenciais,
ativação, HTTP, retries e recibos específicos. Remover a reserva de envios
introduzida para essa integração. Preservar o comportamento do mock, omitindo
telefone/conteúdo de sua representação textual.

`CONFIRMADO`: simulador, autenticação/RBAC, transições e notificações existentes
permanecem no fluxo atual. O adapter não executa ações de domínio. Falha de
notificação posterior ao commit não desfaz domínio; comandos autenticados e
idempotentes da OC79 não são convertidos em histórico de envios.

## Consequências

`CONFIRMADO`: desenvolvimento e testes não precisam de credenciais ou serviço
externo. Listas do mock existem somente em memória e não confirmam entrega real.
Chamadas explícitas repetidas de envio continuam acrescentando mensagens, sem
promessa de idempotência durável ou retry automático.

`PENDENTE DE DEFINIÇÃO`: retomar a integração real da OC82 somente após definir
fornecedor/API, ambiente autorizado, contrato mínimo, credenciais, timeouts,
erros e garantias de reenvio. OC83 trata recepção/webhook; OC84, notificações
reais; OC109, persistência/outbox e reprocessamento. O PR permanece em rascunho
para não encerrar a ocorrência com critérios de integração real pendentes.
