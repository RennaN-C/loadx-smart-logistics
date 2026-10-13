# Entrega de recuperação — OC98

`CONFIRMADO`: RecoveryDelivery desacopla auth do fornecedor. SmtpRecoveryDelivery
usa SMTP_SSL com validação TLS padrão, timeout de cinco segundos e autenticação.
Nenhuma senha de usuário é enviada. A URL HTTPS aprovada contém token somente
no fragmento. Sem configuração, não existe fake de produção. Fake é injetado
somente pelos testes. Falha de transporte emite evento sem destinatário, corpo,
credencial, resposta SMTP ou traceback. Configuração e limites: auth/README.
