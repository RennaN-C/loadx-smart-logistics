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
