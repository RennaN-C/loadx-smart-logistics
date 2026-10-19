# Entrega de recuperação — OC98

`CONFIRMADO`: RecoveryDelivery desacopla auth do fornecedor. SmtpRecoveryDelivery
usa SMTP_SSL com validação TLS padrão, timeout de cinco segundos e autenticação.
Nenhuma senha de usuário é enviada. A URL HTTPS aprovada contém token somente
no fragmento. Sem configuração, não existe fake de produção. Fake é injetado
somente pelos testes. Falha de transporte emite evento sem destinatário, corpo,
credencial, resposta SMTP ou traceback. Configuração e limites: auth/README.

## Modelo visual de recuperação

O SMTP envia `multipart/alternative`: texto puro e HTML responsivo com marca
LoadX, botão de redefinição, validade de 15 minutos, link alternativo e alerta
para solicitação desconhecida. Sem imagens externas, scripts ou rastreamento.
O nome de exibição é **LoadX | Segurança**; o endereço real vem exclusivamente
de `SMTP_SENDER` (não é criada uma conta de e-mail automaticamente).
Token permanece no fragmento do link, sem alterar fluxo MFA, prazo, uso único,
SMTP ou política de segurança. Para uso real, configurar remetente autorizado
com domínio próprio e SPF/DKIM/DMARC, quando disponível.
