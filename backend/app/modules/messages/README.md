# Mensagens

`CONFIRMADO`: router.py preserva simulador /messages/interpret, com sessão,
Origin/CSRF e permissão loadx.messages.manage. Telefone não autentica integração.

`CONFIRMADO`: webhook_router.py recebe eventos HTTP controlados, limitados e
assinados; composição fica em app/integrations/inbound_webhook.py. A execução
é delegada ao ExternalCommandService, sem regra de domínio no router.
Contrato, configuração, erros e mídia desabilitada: [inbound.md](inbound.md).
