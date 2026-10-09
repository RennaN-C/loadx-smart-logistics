# ADR-035: adapter de envio WhatsApp Business — OC82

Status: proposta; escolha do fornecedor e ativação pendentes de confirmação

## Contexto

`CONFIRMADO`: Issue #125 autoriza um adapter substituível, configurável e testável.
OC79 já fornece autenticidade, autorização e deduplicação de comandos de domínio.
Seu registro não representa um recibo de envio ao WhatsApp. OC83 implementará
recepção/webhook; OC84 consumirá o envio; persistência/outbox pertence à OC109.

## Proposta

`RECOMENDAÇÃO`: Meta Cloud API por HTTP usando httpx2 já instalado, sem SDK novo.
Referências oficiais consultadas em 2026-10-09:

- [início e recursos de teste](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started);
- [Messages API](https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/whatsapp-business-phone-number/message-api);
- [mensagens de serviço](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages);
- [coleção oficial Meta](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api).

`DECISÃO NECESSÁRIA`: a equipe ainda deve confirmar Meta como fornecedor, versão
da Graph API e ambiente autorizado. Implementação proposta permanece desativada:
WHATSAPP_PROVIDER=mock e WHATSAPP_REAL_ENABLED=false. Não contratar serviço,
criar templates ou testar com credenciais reais nesta OC.

`RECOMENDAÇÃO`: preservar WhatsAppProvider/send_response e DTO legado; acrescentar
operation_id UUID opcional, provider_message_id e accepted_at UTC ao resultado.
Aceitação pelo provider não significa entrega ao destinatário. Texto livre somente;
o chamador verifica janela de atendimento/consentimento antes do envio. Nenhum
fallback para template inventado. Telefone nacional usa código de país configurado
explicitamente; formato internacional exige prefixo +.

`RECOMENDAÇÃO`: timeout por fase HTTP e tentativas limitados por configuração.
Retry automático somente em falha de conexão/pool comprovadamente anterior ao
POST. Timeout de leitura/escrita, resposta inválida, 408 e 5xx podem esconder
aceitação: não reenviar automaticamente. 4xx/429 também retornam erro normalizado.
Nunca seguir redirects nem usar proxy/credenciais implícitos do ambiente.

`RECOMENDAÇÃO`: SendGuard é uma port opcional de reserva atômica por operation_id
com fingerprint de destinatário/conteúdo. Reserva acontece antes do IO. Repetição
concluída retorna receipt original; payload diferente é conflito; reserva sem
receipt bloqueia reenvio, inclusive após falha ambígua. Provider real recusa envio
com operation_id se não houver guard injetado. Guard em memória é exclusivo de
mock/testes; não compõe o provider real por configuração. Consumer que exige
idempotência precisa fornecer implementação durável, sem inventar tabela na OC82.

`RECOMENDAÇÃO`: simulador HTTP continua exclusivamente mock, mesmo se saída real
for selecionada. Autenticação bearer de envio não autentica remetente. Recepção
real é recusada pelo adapter. OC83 deve passar bytes autenticados e ator confiável
à OC79; somente após seu commit pode enviar resposta, sem repetir domínio quando
receipt.duplicate=true. Falha externa nunca desfaz operação confirmada.

`RECOMENDAÇÃO`: eventos de aceitação/falha/retry usam logger operacional existente,
correlação e códigos fechados. Não registrar telefone, texto, token, endpoint com
identificador do número, body externo ou exception/traceback. Sem fallback mock
silencioso após falha real: trocar configuração explicitamente.

## Limites

`RISCO IDENTIFICADO`: Meta não é tratada como garantia de exactly-once. Sem guard
durável, envios sem operation_id são best-effort e uma nova chamada pode duplicar
mensagem. Mesmo com guard, resultado incerto exige reconciliação, não reenvio.

`PENDENTE DE DEFINIÇÃO`: aprovação do fornecedor e credenciais no ambiente;
bindings/assinatura de entrada OC83; eventos/templates OC84; guard durável,
reprocessamento e reconciliação OC109. Não altera banco, RBAC, endpoints ou estados.
