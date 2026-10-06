# Integrações

## OC79 — autenticidade externa

`CONFIRMADO`: `external_commands.py` define ports de autenticidade e resolução
de ator, adapter HMAC genérico e bindings exclusivos do servidor. Consumers usam
[ExternalCommandService](../modules/external_commands/README.md) para executar;
nenhum provider escreve em tabelas de domínio. Fornecedor/webhook/envio real
pertencem às OCs posteriores. Não há credencial ou integração ativa por padrão.

Adaptadores para serviços externos. O restante do sistema depende de interfaces, não de SDKs específicos.

No desenvolvimento inicial, use providers mock para IA e WhatsApp.
